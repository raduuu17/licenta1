// Theme toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    // Get theme from localStorage or user preference
    function getInitialTheme() {
        // Check if a theme is stored in localStorage
        const storedTheme = localStorage.getItem('theme');
        
        if (storedTheme) {
            return storedTheme;
        }
        
        // Check if user is logged in and has a theme preference
        const userThemeEl = document.getElementById('user-theme-preference');
        if (userThemeEl) {
            const userTheme = userThemeEl.getAttribute('data-theme');
            if (userTheme && ['light', 'dark', 'system'].includes(userTheme)) {
                return userTheme;
            }
        }
        
        // Check if user prefers dark mode at system level
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        
        // Default to light
        return 'light';
    }
    
    // Apply theme to document
    function applyTheme(theme) {
        if (theme === 'system') {
            // Use system preference
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                document.documentElement.setAttribute('data-theme', 'dark');
                updateIcons('dark');
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
                updateIcons('light');
            }
        } else {
            document.documentElement.setAttribute('data-theme', theme);
            updateIcons(theme);
        }
        
        // Store in localStorage for returning visitors
        localStorage.setItem('theme', theme);
    }
    
    // Update the icons to show correct sun/moon based on theme
    function updateIcons(theme) {
        const darkIcons = document.querySelectorAll('.theme-dark-icon');
        const lightIcons = document.querySelectorAll('.theme-light-icon');
        
        if (theme === 'dark') {
            darkIcons.forEach(icon => icon.style.display = 'none');
            lightIcons.forEach(icon => icon.style.display = 'inline-block');
        } else {
            darkIcons.forEach(icon => icon.style.display = 'inline-block');
            lightIcons.forEach(icon => icon.style.display = 'none');
        }
    }
    
    // Apply initial theme
    const initialTheme = getInitialTheme();
    applyTheme(initialTheme);
    
    // Set up theme toggle buttons
    const themeToggleBtns = document.querySelectorAll('.theme-toggle-btn');
    themeToggleBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            applyTheme(newTheme);
            
            // If user is logged in, save preference to server
            if (document.body.classList.contains('user-logged-in')) {
                saveThemePreference(newTheme);
            }
        });
    });
    
    // Save theme preference to server for logged-in users
    function saveThemePreference(theme) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        fetch('/accounts/toggle-theme/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            },
            body: `theme=${theme}`
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                console.error('Failed to save theme preference');
            }
        })
        .catch(error => {
            console.error('Error saving theme preference:', error);
        });
    }
    
    // Listen for system preference changes
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
            if (localStorage.getItem('theme') === 'system') {
                applyTheme('system');
            }
        });
    }
});
