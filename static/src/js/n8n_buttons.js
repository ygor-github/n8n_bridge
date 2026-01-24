/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ChatHub } from "@mail/components/chat_hub/chat_hub";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted } from "@odoo/owl";

/**
 * n8n Quick Reply Handler
 * Detecta clics en botones con clase .n8n-quick-reply y envía el texto como mensaje.
 */
document.addEventListener('click', function (ev) {
    const btn = ev.target.closest('.n8n-quick-reply');
    if (!btn) return;

    const replyText = btn.getAttribute('data-reply') || btn.innerText;

    // Buscar el input del chat activo
    // En Odoo 18 el textarea de la conversación activa suele tener clase .o-mail-Composer-input
    const composer = document.querySelector('.o-mail-Composer-input');

    if (composer) {
        // Inyectar texto y disparar evento de envío
        composer.value = replyText;
        composer.dispatchEvent(new Event('input', { bubbles: true }));

        // Simular Enter para enviar
        const enterEv = new KeyboardEvent('keydown', {
            bubbles: true,
            cancelable: true,
            key: 'Enter',
            code: 'Enter',
            keyCode: 13
        });
        composer.dispatchEvent(enterEv);

        // Opcional: Eliminar los botones después del clic para evitar doble envío
        const container = btn.closest('.n8n-button-container');
        if (container) {
            container.style.opacity = '0.5';
            container.style.pointerEvents = 'none';
        }
    }
});
