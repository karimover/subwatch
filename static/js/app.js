(() => {
    document.querySelectorAll("[data-confirm]").forEach((element) => {
        element.addEventListener("click", (event) => {
            const message = element.dataset.confirm || "Подтвердить действие?";
            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });

    const getCookie = (name) => {
        const prefix = `${name}=`;
        const cookie = document.cookie.split(";").map((item) => item.trim()).find((item) => item.startsWith(prefix));
        return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : "";
    };

    document.querySelectorAll("[data-subscription-toggle]").forEach((button) => {
        button.addEventListener("click", async () => {
            const feedback = document.querySelector("[data-subscription-feedback]");
            const badge = document.querySelector("[data-subscription-status]");
            const nextStatus = button.dataset.nextStatus;
            button.disabled = true;
            if (feedback) feedback.textContent = "Сохраняем статус…";

            try {
                const response = await fetch(button.dataset.apiUrl, {
                    method: "PATCH",
                    credentials: "same-origin",
                    headers: {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "X-CSRFToken": getCookie("csrftoken"),
                    },
                    body: JSON.stringify({ status: nextStatus }),
                });
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const subscription = await response.json();
                const isActive = subscription.status === "active";
                if (badge) {
                    badge.textContent = isActive ? "Активна" : "Приостановлена";
                    badge.className = `status-pill status-${subscription.status}`;
                }
                button.dataset.nextStatus = isActive ? "paused" : "active";
                button.textContent = isActive ? "Приостановить" : "Возобновить";
                if (feedback) feedback.textContent = "Статус обновлён без перезагрузки страницы.";
            } catch (error) {
                if (feedback) feedback.textContent = "Не удалось обновить статус. Обнови страницу и попробуй ещё раз.";
            } finally {
                button.disabled = false;
            }
        });
    });

})();
