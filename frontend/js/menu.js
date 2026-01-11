export function initMenu({
    toggleId = 'menu-toggle',
    sideId   = 'side-menu',
    closeId  = 'close-menu'
} = {}) {
    const toggleBtn = document.getElementById(toggleId);
    const sidePanel = document.getElementById(sideId);
    const closeBtn  = document.getElementById(closeId);

    if (!toggleBtn || !sidePanel || !closeBtn) {
        console.error('[initMenu] One of the required elements is missing in the DOM');
        return null;
    }

    const open = () => {
        sidePanel.classList.add('open');
        toggleBtn.style.display = 'none';
    };
    const close = () => {
        sidePanel.classList.remove('open');
        toggleBtn.style.display = 'block';
    };

    toggleBtn.addEventListener('click', open);
    closeBtn.addEventListener('click', close);

    return { open, close };
}