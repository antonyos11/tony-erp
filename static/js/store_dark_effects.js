/**
 * Tony Store - Dark Theme Interactive Effects
 * تأثيرات متطورة للمتجر الإلكتروني
 */

(function() {
    'use strict';

    // ===== Particles.js Configuration - نجوم متحركة =====
    function initParticles() {
        if (typeof particlesJS === 'undefined') {
            console.log('Particles.js not loaded, skipping particle effects');
            return;
        }

        particlesJS('particles-js', {
            particles: {
                number: {
                    value: 80,
                    density: {
                        enable: true,
                        value_area: 800
                    }
                },
                color: {
                    value: '#d4af37'
                },
                shape: {
                    type: 'circle',
                    stroke: {
                        width: 0,
                        color: '#000000'
                    }
                },
                opacity: {
                    value: 0.5,
                    random: true,
                    anim: {
                        enable: true,
                        speed: 1,
                        opacity_min: 0.1,
                        sync: false
                    }
                },
                size: {
                    value: 3,
                    random: true,
                    anim: {
                        enable: true,
                        speed: 2,
                        size_min: 0.1,
                        sync: false
                    }
                },
                line_linked: {
                    enable: true,
                    distance: 150,
                    color: '#d4af37',
                    opacity: 0.2,
                    width: 1
                },
                move: {
                    enable: true,
                    speed: 2,
                    direction: 'none',
                    random: false,
                    straight: false,
                    out_mode: 'out',
                    bounce: false
                }
            },
            interactivity: {
                detect_on: 'canvas',
                events: {
                    onhover: {
                        enable: true,
                        mode: 'repulse'
                    },
                    onclick: {
                        enable: true,
                        mode: 'push'
                    },
                    resize: true
                },
                modes: {
                    repulse: {
                        distance: 100,
                        duration: 0.4
                    },
                    push: {
                        particles_nb: 4
                    }
                }
            },
            retina_detect: true
        });
    }

    // ===== Smooth Scroll =====
    function initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                const href = this.getAttribute('href');
                if (href === '#' || !href) return;
                
                const target = document.querySelector(href);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    // ===== Scroll Reveal Animations =====
    function initScrollReveal() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in-up');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        // مراقبة العناصر
        document.querySelectorAll('.category-card, .product-card, .feature-item, .section-title').forEach(el => {
            observer.observe(el);
        });
    }

    // ===== Hero Slider مع Auto Play =====
    function initHeroSlider() {
        const slides = document.querySelectorAll('.hero-slide');
        const dots = document.querySelectorAll('.hero-dot');
        let currentSlide = 0;
        let slideInterval;

        if (slides.length === 0) return;

        function showSlide(index) {
            slides.forEach(slide => slide.classList.remove('active'));
            dots.forEach(dot => dot.classList.remove('active'));
            
            slides[index].classList.add('active');
            if (dots[index]) dots[index].classList.add('active');
        }

        function nextSlide() {
            currentSlide = (currentSlide + 1) % slides.length;
            showSlide(currentSlide);
        }

        function startAutoPlay() {
            slideInterval = setInterval(nextSlide, 5000);
        }

        function stopAutoPlay() {
            clearInterval(slideInterval);
        }

        // النقر على النقاط
        dots.forEach((dot, index) => {
            dot.addEventListener('click', () => {
                stopAutoPlay();
                currentSlide = index;
                showSlide(currentSlide);
                startAutoPlay();
            });
        });

        // توقف عند hover
        const heroSection = document.querySelector('.hero-section');
        if (heroSection) {
            heroSection.addEventListener('mouseenter', stopAutoPlay);
            heroSection.addEventListener('mouseleave', startAutoPlay);
        }

        startAutoPlay();
    }

    // ===== Parallax Effect للصور =====
    function initParallax() {
        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            const parallaxElements = document.querySelectorAll('.hero-visual img, .category-image img');
            
            parallaxElements.forEach(el => {
                const speed = 0.5;
                const yPos = -(scrolled * speed);
                el.style.transform = `translateY(${yPos}px)`;
            });
        });
    }

    // ===== Cursor Glow Effect =====
    function initCursorGlow() {
        const cursorGlow = document.createElement('div');
        cursorGlow.className = 'cursor-glow';
        cursorGlow.style.cssText = `
            position: fixed;
            width: 300px;
            height: 300px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(212, 175, 55, 0.15) 0%, transparent 70%);
            pointer-events: none;
            z-index: 9999;
            transform: translate(-50%, -50%);
            transition: opacity 0.3s ease;
            opacity: 0;
        `;
        document.body.appendChild(cursorGlow);

        document.addEventListener('mousemove', (e) => {
            cursorGlow.style.left = e.clientX + 'px';
            cursorGlow.style.top = e.clientY + 'px';
            cursorGlow.style.opacity = '1';
        });

        document.addEventListener('mouseleave', () => {
            cursorGlow.style.opacity = '0';
        });
    }

    // ===== Product Card 3D Tilt Effect =====
    function init3DTilt() {
        const cards = document.querySelectorAll('.product-card, .category-card');
        
        cards.forEach(card => {
            card.addEventListener('mousemove', (e) => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                
                const rotateX = (y - centerY) / 10;
                const rotateY = (centerX - x) / 10;
                
                card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`;
            });
            
            card.addEventListener('mouseleave', () => {
                card.style.transform = '';
            });
        });
    }

    // ===== Floating Animation للأزرار =====
    function initFloatingButtons() {
        const buttons = document.querySelectorAll('.btn-hero, .btn-add-cart');
        
        buttons.forEach((btn, index) => {
            btn.style.animation = `float ${3 + index * 0.5}s ease-in-out infinite`;
        });
    }

    // ===== Counter Animation للإحصائيات =====
    function initCounters() {
        const counters = document.querySelectorAll('[data-count]');
        
        const animateCounter = (counter) => {
            const target = parseInt(counter.dataset.count);
            const duration = 2000;
            const step = target / (duration / 16);
            let current = 0;
            
            const updateCounter = () => {
                current += step;
                if (current < target) {
                    counter.textContent = Math.floor(current);
                    requestAnimationFrame(updateCounter);
                } else {
                    counter.textContent = target;
                }
            };
            
            updateCounter();
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        });
        
        counters.forEach(counter => observer.observe(counter));
    }

    // ===== Loading Animation =====
    function initLoadingAnimation() {
        window.addEventListener('load', () => {
            document.body.classList.add('loaded');
            
            // تأخير ظهور المحتوى بشكل تدريجي
            const elements = document.querySelectorAll('.hero-content, .category-card, .product-card');
            elements.forEach((el, index) => {
                setTimeout(() => {
                    el.style.animation = 'fadeInUp 0.6s ease-out forwards';
                }, index * 100);
            });
        });
    }

    // ===== Wishlist & Cart Animations =====
    function initWishlistCartAnimations() {
        document.addEventListener('click', (e) => {
            // Wishlist animation
            if (e.target.closest('.wishlist-btn, .product-action-btn[data-action="wishlist"]')) {
                const btn = e.target.closest('.wishlist-btn, .product-action-btn');
                btn.classList.add('heart-beat');
                setTimeout(() => btn.classList.remove('heart-beat'), 600);
            }
            
            // Add to cart animation
            if (e.target.closest('.btn-add-cart, .product-action-btn[data-action="cart"]')) {
                const btn = e.target.closest('.btn-add-cart, .product-action-btn');
                
                // Create flying cart icon
                const icon = document.createElement('i');
                icon.className = 'bi bi-cart-plus';
                icon.style.cssText = `
                    position: fixed;
                    left: ${e.clientX}px;
                    top: ${e.clientY}px;
                    font-size: 2rem;
                    color: var(--gold-primary);
                    animation: flyToCart 1s ease-out forwards;
                    pointer-events: none;
                    z-index: 9999;
                `;
                document.body.appendChild(icon);
                
                setTimeout(() => icon.remove(), 1000);
            }
        });
    }

    // ===== Add CSS Animations =====
    function addCustomAnimations() {
        const style = document.createElement('style');
        style.textContent = `
            @keyframes float {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-10px); }
            }
            
            @keyframes heart-beat {
                0%, 100% { transform: scale(1); }
                25% { transform: scale(1.3); }
                50% { transform: scale(1.1); }
                75% { transform: scale(1.2); }
            }
            
            .heart-beat {
                animation: heart-beat 0.6s ease;
            }
            
            @keyframes flyToCart {
                0% {
                    transform: translate(0, 0) scale(1);
                    opacity: 1;
                }
                100% {
                    transform: translate(calc(100vw - 100px), -100px) scale(0.3);
                    opacity: 0;
                }
            }
            
            body.loaded {
                overflow-x: hidden;
            }
        `;
        document.head.appendChild(style);
    }

    // ===== تهيئة كل التأثيرات =====
    function init() {
        // التحقق من تحميل الصفحة
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }

        console.log('🎨 Initializing Tony Store Dark Theme Effects...');

        // تفعيل التأثيرات
        addCustomAnimations();
        initSmoothScroll();
        initScrollReveal();
        initHeroSlider();
        initParallax();
        initCursorGlow();
        init3DTilt();
        initFloatingButtons();
        initCounters();
        initLoadingAnimation();
        initWishlistCartAnimations();
        
        // Particles.js (اختياري - يحتاج مكتبة خارجية)
        if (document.getElementById('particles-js')) {
            initParticles();
        }

        console.log('✅ All effects initialized successfully!');
    }

    // بدء التهيئة
    init();

})();
