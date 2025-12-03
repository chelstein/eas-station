/**
 * EAS Station - Logo Effects
 * Dynamic JavaScript enhancements for the brand logo
 * Version: 2.0
 */

(function() {
    'use strict';

    // ============================================
    // ADD DYNAMIC SVG GRADIENTS
    // ============================================

    function addLogoGradients() {
        const logos = document.querySelectorAll('.logo-wordmark, .brand-logo');

        logos.forEach(logo => {
            if (logo.querySelector('defs')) {
                // Already has defs, skip
                return;
            }

            // Create defs element
            const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');

            // Create animated gradient
            const gradient = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
            gradient.setAttribute('id', 'logoGradient');
            gradient.setAttribute('x1', '0%');
            gradient.setAttribute('y1', '0%');
            gradient.setAttribute('x2', '100%');
            gradient.setAttribute('y2', '0%');

            // Get theme colors
            const primaryColor = getComputedStyle(document.documentElement)
                .getPropertyValue('--primary-color') || '#204885';
            const secondaryColor = getComputedStyle(document.documentElement)
                .getPropertyValue('--secondary-color') || '#872a96';

            // Create gradient stops
            const stop1 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
            stop1.setAttribute('offset', '0%');
            stop1.setAttribute('stop-color', primaryColor);

            const stop2 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
            stop2.setAttribute('offset', '50%');
            stop2.setAttribute('stop-color', secondaryColor);

            const stop3 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
            stop3.setAttribute('offset', '100%');
            stop3.setAttribute('stop-color', primaryColor);

            // Animate the gradient
            const animate = document.createElementNS('http://www.w3.org/2000/svg', 'animate');
            animate.setAttribute('attributeName', 'x1');
            animate.setAttribute('values', '0%;100%;0%');
            animate.setAttribute('dur', '4s');
            animate.setAttribute('repeatCount', 'indefinite');

            gradient.appendChild(stop1);
            gradient.appendChild(stop2);
            gradient.appendChild(stop3);
            gradient.appendChild(animate);

            defs.appendChild(gradient);

            // Insert defs as first child
            logo.insertBefore(defs, logo.firstChild);

            console.log('✨ Logo gradients added');
        });
    }

    // ============================================
    // MAGNETIC LOGO EFFECT
    // ============================================

    function initLogoMagneticEffect() {
        const navbarBrand = document.querySelector('.navbar-brand');
        if (!navbarBrand) return;

        const logo = navbarBrand.querySelector('.logo-wordmark');
        if (!logo) return;

        navbarBrand.addEventListener('mousemove', function(e) {
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;

            const moveX = x * 0.1;
            const moveY = y * 0.1;

            logo.style.transform = `translate(${moveX}px, ${moveY}px)`;
        });

        navbarBrand.addEventListener('mouseleave', function() {
            logo.style.transform = 'translate(0, 0)';
        });
    }

    // ============================================
    // LOGO CLICK EFFECTS
    // ============================================

    function initLogoClickEffects() {
        const navbarBrands = document.querySelectorAll('.navbar-brand');

        navbarBrands.forEach(brand => {
            brand.addEventListener('click', function(e) {
                const logo = this.querySelector('.logo-wordmark');
                if (!logo) return;

                // Add heartbeat effect
                logo.classList.add('heartbeat');
                setTimeout(() => {
                    logo.classList.remove('heartbeat');
                }, 1500);
            });
        });
    }

    // ============================================
    // THEME CHANGE DETECTOR
    // ============================================

    function watchThemeChanges() {
        // Watch for theme changes and update gradients
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'data-theme') {
                    // Theme changed, update gradients
                    setTimeout(() => {
                        updateGradientColors();
                    }, 100);
                }
            });
        });

        observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['data-theme']
        });
    }

    function updateGradientColors() {
        // Update all gradient types for new logo designs
        const gradients = document.querySelectorAll('#logoGradient, #sleekGradient, #primaryGradient, #secondaryGradient, #modernGradient1, #modernGradient2');

        gradients.forEach(gradient => {
            const stops = gradient.querySelectorAll('stop');
            const primaryColor = getComputedStyle(document.documentElement)
                .getPropertyValue('--primary-color') || '#204885';
            const secondaryColor = getComputedStyle(document.documentElement)
                .getPropertyValue('--secondary-color') || '#872a96';
            const accentColor = getComputedStyle(document.documentElement)
                .getPropertyValue('--accent-color') || '#4f6fb3';

            // Update based on gradient type
            if (gradient.id === 'sleekGradient' && stops.length >= 3) {
                stops[0].setAttribute('stop-color', primaryColor);
                stops[1].setAttribute('stop-color', accentColor);
                stops[2].setAttribute('stop-color', secondaryColor);
            } else if (gradient.id === 'primaryGradient' && stops.length >= 2) {
                stops[0].setAttribute('stop-color', primaryColor);
                stops[1].setAttribute('stop-color', accentColor);
            } else if (gradient.id === 'secondaryGradient' && stops.length >= 2) {
                stops[0].setAttribute('stop-color', secondaryColor);
                stops[1].setAttribute('stop-color', accentColor);
            } else if ((gradient.id === 'modernGradient1' || gradient.id === 'logoGradient') && stops.length >= 2) {
                stops[0].setAttribute('stop-color', primaryColor);
                stops[1].setAttribute('stop-color', secondaryColor);
                if (stops.length >= 3) {
                    stops[2].setAttribute('stop-color', primaryColor);
                }
            }
        });

        // Also update SVG text fills
        const textPrimary = document.querySelectorAll('.logo-text-primary');
        const textSecondary = document.querySelectorAll('.logo-text-secondary');
        
        textPrimary.forEach(text => {
            text.setAttribute('fill', primaryColor);
        });
        
        textSecondary.forEach(text => {
            const textSecondaryColor = getComputedStyle(document.documentElement)
                .getPropertyValue('--text-secondary') || '#5a6c8f';
            text.setAttribute('fill', textSecondaryColor);
        });

        console.log('🎨 Logo gradients and colors updated for new theme');
    }

    // ============================================
    // SPECIAL EFFECTS
    // ============================================

    function addRainbowEffect() {
        const logos = document.querySelectorAll('.logo-wordmark');
        logos.forEach(logo => logo.classList.add('rainbow'));
    }

    function removeRainbowEffect() {
        const logos = document.querySelectorAll('.logo-wordmark');
        logos.forEach(logo => logo.classList.remove('rainbow'));
    }

    function addPulseGlow() {
        const logos = document.querySelectorAll('.logo-wordmark');
        logos.forEach(logo => logo.classList.add('pulse-glow'));
    }

    function removePulseGlow() {
        const logos = document.querySelectorAll('.logo-wordmark');
        logos.forEach(logo => logo.classList.remove('pulse-glow'));
    }

    function addMorphEffect() {
        const logos = document.querySelectorAll('.logo-wordmark');
        logos.forEach(logo => logo.classList.add('morph'));
    }

    function removeMorphEffect() {
        const logos = document.querySelectorAll('.logo-wordmark');
        logos.forEach(logo => logo.classList.remove('morph'));
    }

    function addCelebrationEffect() {
        const logos = document.querySelectorAll('.logo-wordmark');
        logos.forEach(logo => logo.classList.add('celebrate'));
    }

    function removeCelebrationEffect() {
        const logos = document.querySelectorAll('.logo-wordmark');
        logos.forEach(logo => logo.classList.remove('celebrate'));
    }

    function shakeLogo() {
        const logos = document.querySelectorAll('.logo-wordmark');
        logos.forEach(logo => {
            logo.classList.add('shake');
            setTimeout(() => {
                logo.classList.remove('shake');
            }, 500);
        });
    }

    // ============================================
    // LOADING STATE
    // ============================================

    function setLogoLoading(loading) {
        const logos = document.querySelectorAll('.logo-wordmark');
        logos.forEach(logo => {
            if (loading) {
                logo.classList.add('loading');
            } else {
                logo.classList.remove('loading');
            }
        });
    }

    // ============================================
    // EASTER EGG - KONAMI CODE
    // ============================================

    function initKonamiCode() {
        const konamiCode = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];
        let konamiIndex = 0;

        document.addEventListener('keydown', (e) => {
            if (e.key === konamiCode[konamiIndex]) {
                konamiIndex++;
                if (konamiIndex === konamiCode.length) {
                    // Konami code completed!
                    activateRainbowMode();
                    konamiIndex = 0;
                }
            } else {
                konamiIndex = 0;
            }
        });
    }

    function activateRainbowMode() {
        addRainbowEffect();
        addCelebrationEffect();

        // Show notification
        if (window.showToast) {
            window.showToast('🌈 Rainbow mode activated!', 'success');
        }

        // Disable after 10 seconds
        setTimeout(() => {
            removeRainbowEffect();
            removeCelebrationEffect();
        }, 10000);
    }

    // ============================================
    // PERFORMANCE MONITORING
    // ============================================

    function checkPerformance() {
        // Check if device can handle animations
        const isMobile = window.innerWidth <= 768;
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        if (isMobile || prefersReducedMotion) {
            // Disable heavy effects
            const logos = document.querySelectorAll('.logo-wordmark');
            logos.forEach(logo => {
                logo.style.animation = 'none';
            });
            console.log('📱 Logo animations reduced for performance');
        }
    }

    // ============================================
    // INITIALIZATION
    // ============================================

    function init() {
        // Check if running in an environment with SVG support
        if (typeof document.createElementNS !== 'function') {
            console.warn('SVG not supported, skipping logo enhancements');
            return;
        }

        // Add gradients
        addLogoGradients();

        // Check performance
        checkPerformance();

        // Init magnetic effect (only on desktop)
        if (window.innerWidth > 768) {
            initLogoMagneticEffect();
        }

        // Init click effects
        initLogoClickEffects();

        // Watch for theme changes
        watchThemeChanges();

        // Easter egg
        initKonamiCode();

        console.log('✨ Logo effects initialized');
    }

    // ============================================
    // OBSERVE NEW LOGOS
    // ============================================

    function observeNewLogos() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.addedNodes.length > 0) {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1) {
                            if (node.classList && (node.classList.contains('logo-wordmark') || node.classList.contains('brand-logo'))) {
                                addLogoGradients();
                            }
                            // Check children
                            const logos = node.querySelectorAll('.logo-wordmark, .brand-logo');
                            if (logos.length > 0) {
                                addLogoGradients();
                            }
                        }
                    });
                }
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    // ============================================
    // ENTRY POINT
    // ============================================

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            init();
            observeNewLogos();
        });
    } else {
        init();
        observeNewLogos();
    }

    // ============================================
    // EXPORT PUBLIC API
    // ============================================

    window.LogoEffects = {
        addRainbow: addRainbowEffect,
        removeRainbow: removeRainbowEffect,
        addPulseGlow: addPulseGlow,
        removePulseGlow: removePulseGlow,
        addMorph: addMorphEffect,
        removeMorph: removeMorphEffect,
        celebrate: addCelebrationEffect,
        stopCelebration: removeCelebrationEffect,
        shake: shakeLogo,
        setLoading: setLogoLoading,
        updateColors: updateGradientColors
    };

    console.log('💡 Logo effects API available: window.LogoEffects');

})();
