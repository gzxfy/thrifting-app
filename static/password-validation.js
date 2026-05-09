/**
 * Password Validation Script
 * Handles real-time password validation with live UI updates
 * Displays checkmarks (✓) when requirements are met, X (✗) when not
 */

// ============ DOM ELEMENTS ============
const passwordInput = document.getElementById('password');
const confirmPasswordInput = document.getElementById('confirm_password');

function hasLength8Plus(password) {
    return password.length >= 8;
}

function hasUppercase(password) {
    return /[A-Z]/.test(password);
}

function hasLowercase(password) {
    return /[a-z]/.test(password);
}

function hasDigit(password) {
    return /\d/.test(password);
}

function hasSpecialChar(password) {
    return /[!@#$%^&*(),.?":{}|<>]/.test(password);
}

function passwordsMatch(password, confirmPassword) {
    return password === confirmPassword && password !== '';
}

function checkRequirement(requirementId, isValid) {
    const requirementElement = document.getElementById(requirementId);
    const iconElement = requirementElement.querySelector('.requirement-icon');
    if (isValid) {
        requirementElement.classList.add('valid');
        requirementElement.classList.remove('invalid');
        iconElement.classList.add('valid');
        iconElement.classList.remove('invalid');
        iconElement.textContent = '✓';
    } else {
        requirementElement.classList.add('invalid');
        requirementElement.classList.remove('valid');
        iconElement.classList.add('invalid');
        iconElement.classList.remove('valid');
        iconElement.textContent = '✗';
    }
}

function updateValidationUI() {
    const password = passwordInput.value;
    const confirmPassword = confirmPasswordInput.value;
    
    checkRequirement('req-length', hasLength8Plus(password));
    checkRequirement('req-uppercase', hasUppercase(password));
    checkRequirement('req-lowercase', hasLowercase(password));
    checkRequirement('req-digit', hasDigit(password));
    checkRequirement('req-specialchar', hasSpecialChar(password));
    checkRequirement('req-match', passwordsMatch(password, confirmPassword));
}

passwordInput.addEventListener('input', updateValidationUI);
confirmPasswordInput.addEventListener('input', updateValidationUI);

updateValidationUI(); // Initial call to set the correct state on page load\

/**
 * Password Validation Script
 * Inspired by: https://github.com/T4jgat/registration_api_client
 * Original author: T4jgat
 * License: [CHECK THEIR LICENSE]
 */