/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import "@website_sale/js/website_sale";

publicWidget.registry.WebsiteSale.include({
    _onChangeCombination: function (ev, $parent, combination) {
        this._super.apply(this, arguments);

        const noteEl = document.querySelector("#vla_variant_note");
        if (!noteEl) {
            return;
        }

        const note = combination.vla_website_variant_note || "";

        if (note) {
            noteEl.innerHTML = note;
            noteEl.classList.remove("d-none");
        } else {
            noteEl.innerHTML = "";
            noteEl.classList.add("d-none");
        }
    },
});