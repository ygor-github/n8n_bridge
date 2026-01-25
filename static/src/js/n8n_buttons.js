/**
 * n8n Bridge - Quick Reply Handler (Shadow DOM Compatible)
 */
(function () {
    'use strict';

    console.log("BRIDGE: n8n_buttons.js (v5 - Input Blocking) cargado.");

    // Función para cerrar el widget de chat
    function closeChat() {
        console.log("BRIDGE: Intentando cerrar el chat...");

        // Buscar el botón de cierre en Shadow DOM
        function findInShadow(root, selector) {
            let el = root.querySelector(selector);
            if (el) return el;
            const allElements = root.querySelectorAll('*');
            for (let i = 0; i < allElements.length; i++) {
                const child = allElements[i];
                if (child.shadowRoot) {
                    const found = findInShadow(child.shadowRoot, selector);
                    if (found) return found;
                }
            }
            return null;
        }

        // Selectores posibles para el botón de cierre (expandidos)
        const closeSelectors = [
            // Selectores específicos de Odoo 18
            'button.o-mail-ChatWindow-command[title*="lose"]',
            'button.o-mail-ChatWindow-command[title*="errar"]',
            '.o-mail-ChatWindow-header button[aria-label*="lose"]',
            '.o-mail-ChatWindow-header button[aria-label*="errar"]',

            // Selectores de LiveChat
            '.o-livechat-LivechatButton-close',
            '.o-livechat-LivechatButton button[title*="lose"]',

            // Selectores genéricos
            '.o_thread_window_close',
            'button[title*="Close"]',
            'button[title*="Cerrar"]',
            'button[aria-label*="Close"]',
            'button[aria-label*="Cerrar"]',

            // Selectores por clase
            '.o_close',
            '.close',
            'button.btn-close',

            // Selectores por ícono
            'button i.fa-times',
            'button i.fa-close',
            'button span.fa-times'
        ];

        for (const selector of closeSelectors) {
            const closeBtn = findInShadow(document, selector);
            if (closeBtn && closeBtn.offsetParent !== null) {
                console.log("BRIDGE: Botón de cierre encontrado con selector:", selector);
                closeBtn.click();
                return true;
            }
        }

        console.warn("BRIDGE: No se encontró el botón de cierre del chat. Intentando método alternativo...");

        // Método alternativo: buscar cualquier botón en el header del chat
        const chatWindow = findInShadow(document, '.o-mail-ChatWindow');
        if (chatWindow) {
            const headerButtons = chatWindow.querySelectorAll('.o-mail-ChatWindow-header button');
            console.log("BRIDGE: Botones encontrados en header:", headerButtons.length);

            // Buscar el botón que probablemente sea el de cerrar (usualmente el último)
            if (headerButtons.length > 0) {
                const lastButton = headerButtons[headerButtons.length - 1];
                console.log("BRIDGE: Haciendo clic en el último botón del header");
                lastButton.click();
                return true;
            }
        }

        console.error("BRIDGE: No se pudo cerrar el chat automáticamente.");
        return false;
    }

    function handleQuickReply(target, ev) {
        const btn = target.closest('.n8n-quick-reply');
        if (!btn) return;

        let replyText = "";
        const href = btn.getAttribute('href') || "";

        // Si es un enlace externo (http/https)
        if (href.startsWith('http')) {
            // Si tiene el atributo data-close-chat, cerrar el widget después de abrir el enlace
            if (btn.getAttribute('data-close-chat') === 'true') {
                setTimeout(() => {
                    closeChat();
                }, 500); // Pequeño delay para que el enlace se abra primero
            }
            return;
        }

        ev.preventDefault();
        ev.stopPropagation();

        // Estrategia 1: Extraer de atributo data-reply (Prioridad máxima)
        const dataReply = btn.getAttribute('data-reply');
        if (dataReply) {
            replyText = dataReply;
        }
        // Estrategia 2: Extraer de href (ej: #reply:Texto)
        else if (href.includes('#reply:')) {
            replyText = decodeURIComponent(href.split('#reply:')[1]);
        }
        // Estrategia 3: Fallback al texto visible si todo lo anterior falló o está vacío
        else if (!replyText) {
            replyText = btn.innerText.trim();
        }

        console.log("BRIDGE: Procesando clic en:", replyText);

        // Función para buscar un elemento dentro de Shadow DOM de forma recursiva
        function findInShadow(root, selector) {
            let el = root.querySelector(selector);
            if (el) return el;

            // Buscar en todos los hijos que puedan tener shadowRoot
            const allElements = root.querySelectorAll('*');
            for (let i = 0; i < allElements.length; i++) {
                const child = allElements[i];
                if (child.shadowRoot) {
                    const found = findInShadow(child.shadowRoot, selector);
                    if (found) return found;
                }
            }
            return null;
        }

        // Buscar el compositor de Odoo 18 (Probamos múltiples selectores conocidos)
        const possibleSelectors = ['.o-mail-Composer-input', '.o_composer_text_field', 'textarea[placeholder*="mensaje"]', 'textarea'];
        let composer = null;

        for (const selector of possibleSelectors) {
            composer = findInShadow(document, selector);
            if (composer && composer.offsetParent !== null) break;
        }

        if (composer) {
            composer.value = replyText;
            composer.dispatchEvent(new Event('input', { bubbles: true }));
            composer.dispatchEvent(new Event('change', { bubbles: true }));

            const enterEv = new KeyboardEvent('keydown', {
                bubbles: true,
                cancelable: true,
                key: 'Enter',
                code: 'Enter',
                keyCode: 13
            });
            composer.dispatchEvent(enterEv);

            // Limpiar el compositor explícitamente después del envío para evitar confusión
            setTimeout(() => {
                composer.value = '';
                composer.dispatchEvent(new Event('input', { bubbles: true }));
                composer.dispatchEvent(new Event('change', { bubbles: true }));
            }, 50);

            const container = btn.closest('.n8n-button-container');
            if (container) {
                container.style.opacity = '0.5';
                container.style.pointerEvents = 'none';
            }
        } else {
            console.error("BRIDGE: No se encontró .o-mail-Composer-input para enviar la respuesta.");
        }
    }

    // Listener global con useCapture: true y soporte para Shadow DOM
    document.addEventListener('click', function (ev) {
        // composedPath() permite ver a través de Shadow Roots
        const path = ev.composedPath();
        for (let i = 0; i < path.length; i++) {
            const el = path[i];
            if (el.classList && el.classList.contains('n8n-quick-reply')) {
                handleQuickReply(el, ev);
                break;
            }
        }
    }, true);

    // ========== BLOQUEO DE INPUT DURANTE RESPUESTAS RÁPIDAS ==========

    // Función para buscar el compositor en Shadow DOM
    function findComposer() {
        function findInShadow(root, selector) {
            let el = root.querySelector(selector);
            if (el) return el;
            const allElements = root.querySelectorAll('*');
            for (let i = 0; i < allElements.length; i++) {
                const child = allElements[i];
                if (child.shadowRoot) {
                    const found = findInShadow(child.shadowRoot, selector);
                    if (found) return found;
                }
            }
            return null;
        }

        const selectors = ['.o-mail-Composer-input', '.o_composer_text_field', 'textarea[placeholder*="mensaje"]'];
        for (const selector of selectors) {
            const composer = findInShadow(document, selector);
            if (composer && composer.offsetParent !== null) {
                return composer;
            }
        }
        return null;
    }

    // Función para bloquear/desbloquear el compositor
    function toggleComposerBlock(shouldBlock) {
        const composer = findComposer();
        if (!composer) return;

        if (shouldBlock) {
            composer.disabled = true;
            composer.placeholder = "Por favor, selecciona una opción arriba ☝️";
            composer.style.backgroundColor = '#f5f5f5';
            composer.style.cursor = 'not-allowed';
            console.log("BRIDGE: Compositor bloqueado - esperando selección de botón");
        } else {
            composer.disabled = false;
            composer.placeholder = "Escribe un mensaje...";
            composer.style.backgroundColor = '';
            composer.style.cursor = '';
            console.log("BRIDGE: Compositor desbloqueado");
        }
    }

    // Función para verificar si hay botones activos
    function checkForActiveButtons() {
        // Buscar contenedores de botones en el DOM
        function findInShadow(root, selector) {
            const elements = root.querySelectorAll(selector);
            if (elements.length > 0) return Array.from(elements);

            const allElements = root.querySelectorAll('*');
            let found = [];
            for (let i = 0; i < allElements.length; i++) {
                const child = allElements[i];
                if (child.shadowRoot) {
                    found = found.concat(findInShadow(child.shadowRoot, selector));
                }
            }
            return found;
        }

        const containers = findInShadow(document, '.n8n-button-container');

        // Filtrar solo contenedores visibles y no deshabilitados
        const activeContainers = containers.filter(container => {
            if (container.offsetParent === null ||
                container.style.pointerEvents === 'none' ||
                container.style.opacity === '0.5') {
                return false;
            }

            // IMPORTANTE: Solo bloquear si tiene botones de respuesta rápida (no enlaces externos)
            const buttons = container.querySelectorAll('.n8n-quick-reply');
            let hasQuickReplyButtons = false;

            for (const btn of buttons) {
                const href = btn.getAttribute('href') || '';
                const hasDataReply = btn.hasAttribute('data-reply');

                // Es un botón de respuesta rápida si:
                // 1. Tiene data-reply, O
                // 2. No es un enlace externo (no empieza con http)
                if (hasDataReply || !href.startsWith('http')) {
                    hasQuickReplyButtons = true;
                    break;
                }
            }

            return hasQuickReplyButtons;
        });

        const hasActiveButtons = activeContainers.length > 0;
        toggleComposerBlock(hasActiveButtons);

        return hasActiveButtons;
    }

    // Observador de mutaciones para detectar nuevos mensajes con botones
    const observer = new MutationObserver((mutations) => {
        // Debounce: esperar un poco antes de verificar
        clearTimeout(window.buttonCheckTimeout);
        window.buttonCheckTimeout = setTimeout(() => {
            checkForActiveButtons();
        }, 100);
    });

    // Iniciar observación del DOM
    observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['style', 'class']
    });

    // Verificación inicial
    setTimeout(() => {
        checkForActiveButtons();
    }, 1000);

    console.log("BRIDGE: Sistema de bloqueo de input activado");
})();
