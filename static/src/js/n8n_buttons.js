/**
 * n8n Bridge - Quick Reply Handler (Shadow DOM Compatible)
 */
(function () {
    'use strict';

    console.log("BRIDGE: n8n_buttons.js (v16 - Global Resolver) cargado.");

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
            console.log("BRIDGE: Enlace externo detectado. Iniciando cierre de chat...");
            // Cerrar el chat para cualquier enlace externo según requerimiento
            setTimeout(() => {
                closeChat();
            }, 600);
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
            const isWelcomeBtn = btn.classList.contains('n8n-welcome-btn') ||
                btn.closest('.n8n-welcome-wrapper');

            if (isWelcomeBtn) {
                console.log("BRIDGE: Resolviendo MENSAJE DE BIENVENIDA (v15).");
                window._n8n_welcome_resolved = true;
                // Marcar todos los n8n-welcome-btn visibles como resueltos
                findAllInShadows('.n8n-welcome-btn').forEach(b => b.classList.add('n8n-resolved'));
            }

            if (container) {
                console.log("BRIDGE: Marcando contenedor como RESUELTO.");
                container.classList.add('n8n-buttons-resolved');
            } else {
                btn.classList.add('n8n-resolved');
                const parent = btn.parentElement;
                if (parent) {
                    parent.querySelectorAll('.n8n-quick-reply').forEach(b => b.classList.add('n8n-resolved'));
                }
            }

            // Forzar actualización inmediata y retardada de la UI para capturar re-renderizados de Odoo
            setTimeout(checkForActiveButtons, 50);
            setTimeout(checkForActiveButtons, 500);
            setTimeout(checkForActiveButtons, 1500);
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

    // --- UTILS PARA SHADOW DOM ---

    function findAllInShadows(selector, root = document) {
        let found = Array.from(root.querySelectorAll(selector));
        const all = root.querySelectorAll('*');
        for (const el of all) {
            if (el.shadowRoot) {
                found = found.concat(findAllInShadows(selector, el.shadowRoot));
            }
        }
        return found;
    }

    function findFirstInShadows(selector, root = document) {
        const el = root.querySelector(selector);
        if (el) return el;

        const all = root.querySelectorAll('*');
        for (const child of all) {
            if (child.shadowRoot) {
                const found = findFirstInShadows(selector, child.shadowRoot);
                if (found) return found;
            }
        }
        return null;
    }

    // Identificar el compositor (Odoo 18+)
    function findComposer() {
        const selectors = [
            '.o-mail-Composer-input',
            '.o-mail-Composer [contenteditable="true"]',
            '.o_composer_text_field',
            '.o_chat_composer_input',
            'textarea[placeholder*="mensaje"]',
            'textarea'
        ];

        for (const selector of selectors) {
            const composer = findFirstInShadows(selector);
            if (composer && composer.isConnected) {
                return composer;
            }
        }
        return null;
    }

    function toggleComposerBlock(shouldBlock) {
        const composer = findComposer();
        if (!composer) {
            // Solo loguear si estamos intentando bloquear y no lo encontramos
            if (shouldBlock) console.warn("BRIDGE: Intento de bloqueo fallido - No se encontró el compositor.");
            return;
        }

        if (!composer.getAttribute('data-original-placeholder')) {
            const original = composer.placeholder || composer.getAttribute('placeholder') || "Escribe un mensaje...";
            composer.setAttribute('data-original-placeholder', original);
        }

        const isCurrentlyBlocked = composer.classList.contains('n8n-composer-blocked');

        if (shouldBlock && !isCurrentlyBlocked) {
            if (composer.tagName === 'TEXTAREA' || composer.tagName === 'INPUT') {
                composer.disabled = true;
            } else {
                composer.setAttribute('contenteditable', 'false');
            }
            composer.classList.add('n8n-composer-blocked');
            const msg = "Selecciona una opción arriba 👆";
            composer.placeholder = msg;
            composer.setAttribute('placeholder', msg);
            console.log("BRIDGE: >>> BLOQUEANDO COMPOSITOR <<<");
        } else if (!shouldBlock && isCurrentlyBlocked) {
            if (composer.tagName === 'TEXTAREA' || composer.tagName === 'INPUT') {
                composer.disabled = false;
            } else {
                composer.setAttribute('contenteditable', 'true');
            }
            composer.classList.remove('n8n-composer-blocked');
            const original = composer.getAttribute('data-original-placeholder');
            composer.placeholder = original;
            composer.setAttribute('placeholder', original);
            console.log("BRIDGE: >>> DESBLOQUEANDO COMPOSITOR <<<");
        }
    }

    function checkForActiveButtons() {
        const allButtons = findAllInShadows('.n8n-quick-reply');

        // Diagnóstico si encontramos botones pero no se bloquea
        if (allButtons.length > 0) {
            console.log("BRIDGE (Diag): Botones encontrados en el DOM: " + allButtons.length);
        }

        const activeButtons = allButtons.filter(btn => {
            // --- Lógica Global de Bienvenida ---
            // Si el flag global está activo, cualquier botón de bienvenida está resuelto
            const isWelcomeBtn = btn.classList.contains('n8n-welcome-btn') ||
                btn.closest('.n8n-welcome-wrapper');

            if (window._n8n_welcome_resolved && isWelcomeBtn) {
                // Forzar clase resolved por si Odoo re-renderizó
                if (!btn.classList.contains('n8n-resolved')) {
                    btn.classList.add('n8n-resolved');
                }
                return false;
            }

            // 1. Si el botón mismo está resuelto
            if (btn.classList.contains('n8n-resolved')) return false;

            // 2. Si el contenedor está marcado como resuelto
            const container = btn.closest('.n8n-button-container');
            if (container && container.classList.contains('n8n-buttons-resolved')) {
                return false;
            }

            const target = container || btn;
            const style = window.getComputedStyle(target);

            const isVisible = target.isConnected &&
                style.display !== 'none' &&
                style.opacity !== '0.5' &&
                style.pointerEvents !== 'none' &&
                style.filter.indexOf('grayscale') === -1;
            return isVisible;
        });

        if (activeButtons.length > 0) {
            console.log("BRIDGE (Diag): Botones ACTIVOS tras filtro: " + activeButtons.length);
        }

        toggleComposerBlock(activeButtons.length > 0);
    }

    // --- SETUP ---

    const observedRoots = new Set();
    function attachObserver(root) {
        if (!root || observedRoots.has(root)) return;
        observedRoots.add(root);
        console.log("BRIDGE: Observando nuevo Shadow Root/Elemento...");

        const observer = new MutationObserver(() => {
            clearTimeout(window._n8n_check_timer);
            window._n8n_check_timer = setTimeout(checkForActiveButtons, 500);
        });

        observer.observe(root, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['style', 'class']
        });

        // Recursión para Shadow Roots hijos
        const children = root.querySelectorAll('*');
        for (const child of children) {
            if (child.shadowRoot) attachObserver(child.shadowRoot);
        }
    }

    // Monitoreo constante
    attachObserver(document.body);
    setInterval(() => {
        // Buscar proactivamente el root de livechat
        const lr = document.querySelector('.o-livechat-root');
        if (lr && lr.shadowRoot) attachObserver(lr.shadowRoot);

        // Ejecutar chequeo preventivo
        checkForActiveButtons();
    }, 2000);

    setTimeout(checkForActiveButtons, 3000);

    console.log("BRIDGE: Sistema de bloqueo (v16 - Global Resolver) inicializado.");
})();
