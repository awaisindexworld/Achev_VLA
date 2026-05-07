# -*- coding: utf-8 -*-
# from odoo import http


# class TestReports(http.Controller):
#     @http.route('/test_reports/test_reports', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/test_reports/test_reports/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('test_reports.listing', {
#             'root': '/test_reports/test_reports',
#             'objects': http.request.env['test_reports.test_reports'].search([]),
#         })

#     @http.route('/test_reports/test_reports/objects/<model("test_reports.test_reports"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('test_reports.object', {
#             'object': obj
#         })

