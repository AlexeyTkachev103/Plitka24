document.querySelectorAll('form[data-cart-add]').forEach((form) => {
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const button = form.querySelector('button');
        const status = form.querySelector('[role="status"]');
        button.disabled = true;
        try {
            const response = await fetch(form.getAttribute('action'), {
                method: 'POST',
                headers: { Accept: 'application/json' },
                body: new FormData(form),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error);
            document.getElementById('cart-count').textContent = data.count;
            button.textContent = 'Добавить ещё';
            status.textContent = 'Товар добавлен в корзину.';
            status.classList.add('sr-only');
        } catch (error) {
            status.textContent = 'Не удалось добавить товар. Обновите страницу и попробуйте снова.';
            status.classList.remove('sr-only');
        } finally {
            button.disabled = false;
        }
    });
});
