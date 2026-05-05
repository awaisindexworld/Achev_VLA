import base64
import os
import requests
import datetime
import hashlib
import hmac
import json
import logging
import subprocess
import tempfile
import time
from urllib.parse import urlparse

from odoo import models, fields

_logger = logging.getLogger(__name__)


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    # ── Writing fields ──────────────────────────────────────────────────────
    writing_job_id = fields.Char("Writing Job ID")
    writing_clb = fields.Integer("Writing CLB", readonly=True)

    # ── Speaking fields ─────────────────────────────────────────────────────
    speaking_job_id = fields.Char("Speaking Job ID")
    speaking_clb = fields.Integer("Speaking CLB", readonly=True)
    speaking_clb_received = fields.Boolean("Speaking CLB Received", default=False, readonly=True)

    # Writing endpoints
    POST_URL = "https://hn6zaea9y9.execute-api.ca-central-1.amazonaws.com/dev/score-jobs"
    GET_URL = "https://r2os6woa13.execute-api.ca-central-1.amazonaws.com/dev/score-jobs/{}"

    # Speaking endpoints
    SPEAKING_POST_URL = "https://wut0ticeo4.execute-api.ca-central-1.amazonaws.com/speaking/jobs"
    SPEAKING_GET_URL = "https://2mbowdmiz3.execute-api.ca-central-1.amazonaws.com/speaking/jobs/{}"

    # ================= AWS SIGN =================
    def _sign(self, key, msg):
        return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

    def _get_signature_key(self, key, date_stamp, region, service):
        k_date = self._sign(('AWS4' + key).encode('utf-8'), date_stamp)
        k_region = self._sign(k_date, region)
        k_service = self._sign(k_region, service)
        k_signing = self._sign(k_service, 'aws4_request')
        return k_signing

    def _aws_request(self, method, url, payload=""):
        ICP = self.env['ir.config_parameter'].sudo()
        access_key = ICP.get_param('vla_apis.aws_access_key', '')
        secret_key = ICP.get_param('vla_apis.aws_secret_key', '')
        region = ICP.get_param('vla_apis.aws_region', 'ca-central-1')
        service = ICP.get_param('vla_apis.aws_service', 'execute-api')

        parsed = urlparse(url)
        host = parsed.netloc
        canonical_uri = parsed.path
        canonical_querystring = parsed.query or ''

        t = datetime.datetime.utcnow()
        amz_date = t.strftime('%Y%m%dT%H%M%SZ')
        date_stamp = t.strftime('%Y%m%d')

        payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()

        canonical_headers = f'host:{host}\nx-amz-date:{amz_date}\n'
        signed_headers = 'host;x-amz-date'

        canonical_request = '\n'.join([
            method,
            canonical_uri,
            canonical_querystring,
            canonical_headers,
            signed_headers,
            payload_hash
        ])

        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f'{date_stamp}/{region}/{service}/aws4_request'

        string_to_sign = '\n'.join([
            algorithm,
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
        ])

        signing_key = self._get_signature_key(secret_key, date_stamp, region, service)

        signature = hmac.new(
            signing_key, string_to_sign.encode('utf-8'), hashlib.sha256
        ).hexdigest()

        authorization_header = (
            f'{algorithm} Credential={access_key}/{credential_scope}, '
            f'SignedHeaders={signed_headers}, Signature={signature}'
        )

        headers = {
            'x-amz-date': amz_date,
            'Authorization': authorization_header,
            'Content-Type': 'application/json',
        }

        try:
            response = requests.request(method, url, data=payload, headers=headers)
            _logger.info("AWS %s RESPONSE: %s", method, response.text)
            return response.json()
        except Exception as e:
            _logger.error("AWS REQUEST ERROR: %s", str(e))
            return {}

    # ================= TRIGGER (state → done) =================
    def write(self, vals):
        res = super().write(vals)

        if 'state' in vals:
            for record in self:
                skill = getattr(record.survey_id, 'assessment_skill_type', None)
                if record.state == 'done':
                    if skill == 'writing' and not record.writing_job_id:
                        record._send_writing_to_api()
                    elif skill == 'speaking' and not record.speaking_job_id:
                        record._send_speaking_to_api()

        return res

    # ═══════════════════════════════════════════════════════════════════════
    #  WRITING API
    # ═══════════════════════════════════════════════════════════════════════

    def _send_writing_to_api(self):
        records = []
        for line in self.user_input_line_ids:
            if line.question_id.question_type == 'text_box' and line.value_text_box:
                records.append({
                    "record_id": str(line.id or 0),
                    "question": line.question_id.title,
                    "answer": line.value_text_box,
                })

        if not records:
            return

        payload = json.dumps({"records": records})
        response = self._aws_request("POST", self.POST_URL, payload)
        job_id = response.get("job_id")

        if job_id:
            self.write({"writing_job_id": job_id})
            self._auto_fetch_writing_clb()

    def _auto_fetch_writing_clb(self):
        """Retry up to 5 times (3 s apart) so the job has time to reach COMPLETED."""
        for record in self:
            if not record.writing_job_id:
                continue
            try:
                url = self.GET_URL.format(record.writing_job_id)

                clb_int = None

                for attempt in range(1, 6):
                    response = self._aws_request("GET", url)
                    status = response.get("status") if response else None
                    _logger.info(
                        "Writing CLB fetch attempt %d/5: job=%s status=%s response=%s",
                        attempt, record.writing_job_id, status, response,
                    )

                    if not response:
                        break

                    if status == "COMPLETED":
                        results = response.get("result", {}).get("results", [])
                        if results:
                            clb_values = [
                                r.get("clb_level") for r in results
                                if r.get("clb_level") is not None
                            ]
                            _logger.info(
                                "Writing CLB: job=%s clb_values=%s",
                                record.writing_job_id, clb_values,
                            )
                            if clb_values:
                                clb_int = round(sum(float(c) for c in clb_values) / len(clb_values))
                                _logger.info(
                                    "Writing CLB: job=%s averaged %d value(s) → %s",
                                    record.writing_job_id, len(clb_values), clb_int,
                                )
                        else:
                            _logger.warning("Writing CLB: COMPLETED but no results for job %s", record.writing_job_id)
                        break

                    if attempt < 5:
                        _logger.info("Writing CLB: job %s not ready, waiting 3 s", record.writing_job_id)
                        time.sleep(3)

                if clb_int is not None:
                    record.writing_clb = clb_int
                    _logger.info("Writing CLB saved: %s for job %s", clb_int, record.writing_job_id)
                    attendee = getattr(record, 'slide_channel_partner_id', False)
                    if attendee:
                        attendee.sudo().write({'writing_clb': str(clb_int)})
                else:
                    _logger.warning(
                        "Writing CLB: could not retrieve CLB for job %s after 5 attempts",
                        record.writing_job_id,
                    )

            except Exception as e:
                _logger.error("Writing CLB fetch error for record %s: %s", record.id, str(e))

    # ═══════════════════════════════════════════════════════════════════════
    #  SPEAKING API
    # ═══════════════════════════════════════════════════════════════════════

    def _convert_audio_to_mp3(self, audio_data, filename):
        """Convert audio bytes to mp3 using ffmpeg. Returns (data, mimetype, filename)."""
        tmp_in = tmp_out = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as f:
                f.write(audio_data)
                tmp_in = f.name

            tmp_out = tmp_in[:-5] + '.mp3'

            result = subprocess.run(
                ['ffmpeg', '-y', '-i', tmp_in, '-vn', tmp_out],
                capture_output=True,
                timeout=60,
            )

            if result.returncode != 0:
                _logger.error("Speaking API: ffmpeg conversion failed: %s",
                              result.stderr.decode(errors='replace'))
                return audio_data, 'audio/webm', filename

            with open(tmp_out, 'rb') as f:
                mp3_data = f.read()

            mp3_filename = (filename.rsplit('.', 1)[0] if '.' in filename else filename) + '.mp3'
            _logger.info("Speaking API: converted to mp3 — %d → %d bytes", len(audio_data), len(mp3_data))
            return mp3_data, 'audio/mpeg', mp3_filename

        except Exception as e:
            _logger.error("Speaking API: audio conversion error: %s", e)
            return audio_data, 'audio/webm', filename

        finally:
            for path in (tmp_in, tmp_out):
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except Exception:
                        pass

    def _send_speaking_to_api(self):
        """POST+PUT for every audio attachment in the survey (one job per question)."""
        # ── 1. Collect ALL audio attachments ────────────────────────────
        audio_items = []

        _logger.info("Speaking API: scanning %d lines for audio attachments (user_input=%s)",
                     len(self.user_input_line_ids), self.id)

        for line in self.user_input_line_ids:
            attachment = getattr(line, 'attachment_id', False)
            _logger.info("Speaking API: line=%s q_type=%s attachment=%s datas_ok=%s",
                         line.id,
                         line.question_id.question_type if line.question_id else 'n/a',
                         attachment.id if attachment else False,
                         bool(attachment and attachment.datas))
            if attachment and attachment.datas:
                audio_data = base64.b64decode(attachment.datas)
                raw_mime = getattr(line, 'mimetype', None) or attachment.mimetype or 'audio/webm'
                mimetype = raw_mime.split(';')[0].strip()
                filename = attachment.name or f'audio_{self.partner_id.id}_{line.id}.webm'
                _logger.info("Speaking API: found audio — filename=%s mimetype=%s size=%d bytes",
                             filename, mimetype, len(audio_data))
                audio_items.append((audio_data, mimetype, filename))

        if not audio_items:
            _logger.warning("Speaking API: no audio attachments found for user_input %s — "
                            "check that vla_audio_assessment is installed and audio was recorded",
                            self.id)
            return

        # ── 2. POST + PUT for each audio ─────────────────────────────────
        client_id = f"partner_{self.partner_id.id or 0}"
        job_ids = []

        for idx, (audio_data, mimetype, filename) in enumerate(audio_items, 1):
            _logger.info("Speaking API: processing audio %d/%d", idx, len(audio_items))

            audio_data, mimetype, filename = self._convert_audio_to_mp3(audio_data, filename)

            post_payload = json.dumps({
                "client_id": client_id,
                "filename": filename,
                "content_type": mimetype,
                "expires_in_seconds": 900,
            })

            post_response = self._aws_request("POST", self.SPEAKING_POST_URL, post_payload)
            job_id = post_response.get("job_id")
            upload_url = post_response.get("upload_url")
            upload_headers = post_response.get("upload_headers") or {"Content-Type": mimetype}

            if not job_id or not upload_url:
                _logger.error("Speaking API: POST failed for audio %d — response=%s",
                              idx, post_response)
                continue

            _logger.info("Speaking API: audio %d job_id=%s, uploading (%d bytes)",
                         idx, job_id, len(audio_data))

            try:
                put_response = requests.put(upload_url, data=audio_data,
                                            headers=upload_headers, timeout=60)
                _logger.info("Speaking API PUT: job=%s status=%s", job_id, put_response.status_code)
                if put_response.status_code not in (200, 204):
                    _logger.error("Speaking API PUT failed: status=%s body=%s",
                                  put_response.status_code, put_response.text)
                else:
                    job_ids.append(job_id)
            except Exception as e:
                _logger.error("Speaking API PUT error for job %s: %s", job_id, str(e))

        if job_ids:
            self.write({"speaking_job_id": ','.join(job_ids)})
            _logger.info("Speaking API: saved %d job_id(s): %s", len(job_ids), job_ids)
        else:
            _logger.error("Speaking API: no jobs successfully submitted for user_input %s", self.id)

    def _fetch_speaking_clb(self):
        """GET speaking results for all jobs. Average CLBs once all jobs are COMPLETED."""
        for record in self:
            if not record.speaking_job_id:
                continue
            try:
                job_ids = [j.strip() for j in record.speaking_job_id.split(',') if j.strip()]
                all_clb_values = []
                all_completed = True

                for job_id in job_ids:
                    url = self.SPEAKING_GET_URL.format(job_id)
                    response = self._aws_request("GET", url)
                    status = response.get("status") if response else None
                    _logger.info("Speaking CLB GET: job=%s status=%s", job_id, status)

                    if status != "COMPLETED":
                        all_completed = False
                        continue

                    results = response.get("result", {}).get("results", [])
                    _logger.info("Speaking CLB results: job=%s results=%s", job_id, results)

                    if not results:
                        _logger.warning("Speaking CLB: COMPLETED but no results for job %s", job_id)
                        continue

                    clb_values = [
                        r.get("clb_level") for r in results
                        if r.get("clb_level") is not None
                    ]
                    _logger.info("Speaking CLB: job=%s clb_values=%s", job_id, clb_values)
                    all_clb_values.extend(clb_values)

                if not all_completed:
                    _logger.info("Speaking CLB: jobs still processing for user_input %s, will retry", record.id)
                    continue

                if not all_clb_values:
                    _logger.warning("Speaking CLB: all jobs completed but no CLB values for user_input %s", record.id)
                    continue

                clb_int = round(sum(float(c) for c in all_clb_values) / len(all_clb_values))
                _logger.info("Speaking CLB: averaged %d value(s) across %d job(s) → %s",
                             len(all_clb_values), len(job_ids), clb_int)

                record.write({'speaking_clb': clb_int, 'speaking_clb_received': True})
                _logger.info("Speaking CLB saved: %s for user_input %s", clb_int, record.id)

                attendee = getattr(record, 'slide_channel_partner_id', False)
                if attendee:
                    attendee.sudo().write({'speaking_clb': str(clb_int)})

            except Exception as e:
                _logger.error("Speaking CLB GET error for record %s: %s", record.id, str(e))

    def _cron_fetch_speaking_clb(self):
        """Cron: fetch CLB for speaking assessments where job was submitted but CLB not yet received."""
        pending = self.search([
            ('speaking_job_id', '!=', False),
            ('speaking_clb_received', '=', False),
            ('state', '=', 'done'),
        ])
        if not pending:
            return
        _logger.info("Speaking CLB cron: processing %d pending record(s)", len(pending))
        pending._fetch_speaking_clb()

    # ================= BUTTON GET (writing – kept for manual retry) =================
    def action_fetch_writing_clb(self):
        for record in self:
            if not record.writing_job_id:
                raise ValueError("No Job ID found. Please complete the survey first.")

            url = self.GET_URL.format(record.writing_job_id)
            response = self._aws_request("GET", url)

            if not response:
                raise ValueError("No response from API.")
            if response.get("status") != "COMPLETED":
                raise ValueError("Result not ready yet. Try again later.")

            results = response.get("result", {}).get("results", [])
            if not results:
                raise ValueError("No results found in API response.")

            clb_values = [r.get("clb_level") for r in results if r.get("clb_level") is not None]
            if not clb_values:
                raise ValueError("CLB level missing in response.")

            clb_int = round(sum(float(c) for c in clb_values) / len(clb_values))
            record.writing_clb = clb_int
            _logger.info("CLB Updated (avg of %d): %s", len(clb_values), clb_int)

            attendee = getattr(record, 'slide_channel_partner_id', False)
            if attendee:
                attendee.sudo().write({'writing_clb': str(clb_int)})
