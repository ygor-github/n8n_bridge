import { markup } from "@odoo/owl";
import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";

/**
 * Parche para el modelo Thread de Odoo 18.
 * Intercepta la creación del mensaje virtual de bienvenida para desescapar el HTML
 * y marcarlo como seguro (markup) para que OWL lo renderice como HTML real.
 */
patch(Thread.prototype, {
    setup() {
        super.setup();

        // Helper para desescapar HTML (Robusto)
        const unescapeHTML = (str) => {
            if (!str) return "";
            // 1. Limpieza de links anidados proyectados por el sanitizer de Odoo
            let cleaned = str.replace(/href="<a\s+href="([^"]+)"[^>]*>.*?<\/a>"/g, 'href="$1"');
            cleaned = cleaned.replace(/target="_blank">https?:\/\/.*?<\/a>/g, 'target="_blank">');

            // 2. Unescape via textarea
            const txt = document.createElement("textarea");
            txt.innerHTML = cleaned;
            let unescaped = txt.value;

            // 3. Manejar double escaping recurrente
            let limit = 0;
            while (unescaped.includes('&lt;') && limit < 3) {
                txt.innerHTML = unescaped;
                unescaped = txt.value;
                limit++;
            }
            return unescaped;
        };

        // Sobrescribimos el Record Message virtual de bienvenida
        this.livechatWelcomeMessage = Record.one("Message", {
            compute() {
                if (this.hasWelcomeMessage) {
                    const livechatService = this.store.env.services["im_livechat.livechat"];
                    const options = (livechatService && livechatService.options) || {};
                    let body = options.default_message || "";

                    console.log("BRIDGE (Patch): Processing virtual message. Raw body length:", body.length);

                    // Si el bridge de n8n indica que debemos permitir HTML (o si detectamos patrones n8n)
                    if (options.n8n_enable_html_welcome || body.includes('n8n-button-container')) {
                        try {
                            // Detectamos si el mensaje viene escapado o en bloques <pre>
                            if (body.includes('&lt;') || body.includes('n8n-button-container') || body.includes('<pre')) {
                                console.log("BRIDGE (Patch): Welcome message needs healing. Healing...");

                                // Sanar el contenido
                                body = unescapeHTML(body);

                                // Etiquetar botones de bienvenida para rastreo robusto (más flexible con comillas y espacios)
                                body = body.replace(/class\s*=\s*["']([^"']*n8n-quick-reply[^"']*)["']/g, 'class="$1 n8n-welcome-btn"');

                                // Eliminar envolturas PRE si existen
                                body = body.replace(/<pre[^>]*>/g, '').replace(/<\/pre>/g, '');

                                // CRITICAL: Marcar como HTML seguro para OWL
                                body = markup(`<div class="n8n-welcome-wrapper">${body}</div>`);
                                console.log("BRIDGE (Patch): Welcome message HEALED and marked as SAFE HTML with wrapper.");
                            } else if (body.includes('<p') || body.includes('<div')) {
                                // Si ya tiene tags pero no está escapado, igual marcamos como markup para asegurar renderizado
                                body = markup(body);
                                console.log("BRIDGE (Patch): Welcome message marked as SAFE HTML (was already unescaped).");
                            }
                        } catch (e) {
                            console.error("BRIDGE (Patch): Error during healing process:", e);
                        }
                    } else {
                        console.log("BRIDGE (Patch): HTML welcome disabled or no buttons found. Sending as is.");
                    }

                    return {
                        id: -0.2 - this.id,
                        body: body,
                        thread: this,
                        author: this.operator,
                    };
                }
            },
        });
    },
});
