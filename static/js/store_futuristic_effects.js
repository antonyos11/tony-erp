/**
 * Tony Store - Futuristic Interactive Effects
 * التأثيرات التفاعلية المستقبلية
 */

(function() {
    'use strict';

    // ===== 3D Parallax Mouse Tracking =====
    function init3DParallax() {
        const cards = document.querySelectorAll('.product-capsule, .category-futuristic');
        
        cards.forEach(card => {
            card.addEventListener('mousemove', (e) => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                
                const rotateX = (y - centerY) / 15;
                const rotateY = (centerX - x) / 15;
                
                card.style.transform = `
                    perspective(1000px)
                    rotateX(${rotateX}deg)
                    rotateY(${rotateY}deg)
                    translateY(-15px)
                    scale(1.02)
                `;
            });
            
            card.addEventListener('mouseleave', () => {
                card.style.transform = '';
            });
        });
    }

    // ===== Exploded 3D Layer View =====
    function initLayeredView() {
        const layerContainer = document.querySelector('.layer-exploded-view');
        if (!layerContainer) return;

        const layers = layerContainer.querySelectorAll('.mattress-layer');
        let currentLayer = 0;

        // Auto-explode on scroll
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    setTimeout(() => {
                        layerContainer.classList.add('exploded');
                    }, 500);
                    
                    // Highlight layers one by one
                    layers.forEach((layer, index) => {
                        setTimeout(() => {
                            layers.forEach(l => l.classList.remove('active'));
                            layer.classList.add('active');
                        }, 1500 + (index * 1000));
                    });
                }
            });
        }, { threshold: 0.5 });

        observer.observe(layerContainer);

        // Click to focus on specific layer
        layers.forEach((layer, index) => {
            layer.addEventListener('click', () => {
                layers.forEach(l => l.classList.remove('active'));
                layer.classList.add('active');
            });
        });
    }

    // ===== Interactive Sliders =====
    function initInteractiveSliders() {
        const sliders = document.querySelectorAll('.slider-futuristic');
        
        sliders.forEach(slider => {
            const track = slider.querySelector('.slider-track');
            const thumb = slider.querySelector('.slider-thumb');
            if (!track || !thumb) return;

            let isDragging = false;

            const updateSlider = (x) => {
                const rect = slider.getBoundingClientRect();
                let percentage = ((x - rect.left) / rect.width) * 100;
                percentage = Math.max(0, Math.min(100, percentage));
                
                track.style.width = percentage + '%';
                thumb.style.right = (100 - percentage) + '%';
                
                // Dispatch custom event
                slider.dispatchEvent(new CustomEvent('sliderchange', {
                    detail: { value: percentage }
                }));
            };

            thumb.addEventListener('mousedown', (e) => {
                isDragging = true;
                e.preventDefault();
            });

            document.addEventListener('mousemove', (e) => {
                if (isDragging) {
                    updateSlider(e.clientX);
                }
            });

            document.addEventListener('mouseup', () => {
                isDragging = false;
            });

            slider.addEventListener('click', (e) => {
                if (!isDragging) {
                    updateSlider(e.clientX);
                }
            });
        });
    }

    // ===== Cart Drawer Animation =====
    function initCartDrawer() {
        const cartButton = document.querySelector('[data-cart-toggle]');
        const cartDrawer = document.querySelector('.cart-drawer-glass');
        const closeButton = document.querySelector('[data-cart-close]');

        if (!cartButton || !cartDrawer) return;

        cartButton.addEventListener('click', () => {
            cartDrawer.classList.add('open');
            document.body.style.overflow = 'hidden';
        });

        if (closeButton) {
            closeButton.addEventListener('click', () => {
                cartDrawer.classList.remove('open');
                document.body.style.overflow = '';
            });
        }

        // Close on click outside
        cartDrawer.addEventListener('click', (e) => {
            if (e.target === cartDrawer) {
                cartDrawer.classList.remove('open');
                document.body.style.overflow = '';
            }
        });
    }

    // ===== Search Orb Expansion =====
    function initSearchOrb() {
        const searchOrb = document.querySelector('.search-orb');
        if (!searchOrb) return;

        searchOrb.addEventListener('click', () => {
            // Create full-screen search overlay
            const overlay = document.createElement('div');
            overlay.className = 'search-overlay-glass';
            overlay.innerHTML = `
                <div class="search-overlay-content glass-card">
                    <button class="search-close">&times;</button>
                    <div class="search-input-wrapper">
                        <i class="bi bi-search"></i>
                        <input type="text" placeholder="ابحث عن المنتج المثالي..." autofocus>
                    </div>
                    <div class="search-suggestions"></div>
                </div>
            `;
            
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(10, 22, 40, 0.95);
                backdrop-filter: blur(30px);
                z-index: 9999;
                display: flex;
                align-items: center;
                justify-content: center;
                opacity: 0;
                transition: opacity 0.4s ease;
            `;
            
            document.body.appendChild(overlay);
            setTimeout(() => overlay.style.opacity = '1', 10);

            // Close button
            overlay.querySelector('.search-close').addEventListener('click', () => {
                overlay.style.opacity = '0';
                setTimeout(() => overlay.remove(), 400);
            });

            // Search as you type
            const input = overlay.querySelector('input');
            input.addEventListener('input', (e) => {
                // Implement search logic here
                console.log('Searching for:', e.target.value);
            });
        });
    }

    // ===== Floating Capsules Animation =====
    function initFloatingCapsules() {
        const capsules = document.querySelectorAll('.floating-capsule');
        
        capsules.forEach((capsule, index) => {
            capsule.style.animationDelay = `${index * 0.3}s`;
            
            // Add random floating variation
            const randomDuration = 6 + Math.random() * 4;
            capsule.style.animationDuration = `${randomDuration}s`;
        });
    }

    // ===== Progress Timeline Animation =====
    function initTimelineProgress() {
        const timeline = document.querySelector('.timeline-glow');
        if (!timeline) return;

        const steps = timeline.querySelectorAll('.timeline-step');
        let currentStep = 0;

        const activateStep = (index) => {
            steps.forEach((step, i) => {
                if (i <= index) {
                    step.classList.add('active');
                } else {
                    step.classList.remove('active');
                }
            });
        };

        // Auto-progress (for demo)
        setInterval(() => {
            currentStep = (currentStep + 1) % steps.length;
            activateStep(currentStep);
        }, 3000);

        // Manual click
        steps.forEach((step, index) => {
            step.addEventListener('click', () => {
                currentStep = index;
                activateStep(currentStep);
            });
        });
    }

    // ===== Smooth Scroll Reveal =====
    function initScrollReveal() {
        const revealElements = document.querySelectorAll('.product-capsule, .category-futuristic, .glass-card');
        
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -100px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry, index) => {
                if (entry.isIntersecting) {
                    setTimeout(() => {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                    }, index * 100);
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        revealElements.forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(50px)';
            el.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
            observer.observe(el);
        });
    }

    // ===== Navigation Glassmorphism on Scroll =====
    function initNavGlass() {
        const nav = document.querySelector('.nav-futuristic');
        if (!nav) return;

        window.addEventListener('scroll', () => {
            if (window.scrollY > 100) {
                nav.classList.add('scrolled');
            } else {
                nav.classList.remove('scrolled');
            }
        });
    }

    // ===== Cursor Spotlight Effect =====
    function initCursorSpotlight() {
        const spotlight = document.createElement('div');
        spotlight.className = 'cursor-spotlight';
        spotlight.style.cssText = `
            position: fixed;
            width: 600px;
            height: 600px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(212, 165, 116, 0.08) 0%, transparent 70%);
            pointer-events: none;
            z-index: 9998;
            transform: translate(-50%, -50%);
            transition: opacity 0.3s ease;
            opacity: 0;
        `;
        document.body.appendChild(spotlight);

        document.addEventListener('mousemove', (e) => {
            spotlight.style.left = e.clientX + 'px';
            spotlight.style.top = e.clientY + 'px';
            spotlight.style.opacity = '1';
        });

        document.addEventListener('mouseleave', () => {
            spotlight.style.opacity = '0';
        });
    }

    // ===== AR View Simulation (Placeholder) =====
    function initARView() {
        const arButtons = document.querySelectorAll('[data-ar-view]');
        
        arButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                // Create AR overlay
                const arOverlay = document.createElement('div');
                arOverlay.innerHTML = `
                    <div class="ar-viewer glass-card">
                        <div class="ar-header">
                            <h3>الواقع المعزز</h3>
                            <button class="ar-close">&times;</button>
                        </div>
                        <div class="ar-viewport">
                            <div class="ar-placeholder">
                                <i class="bi bi-camera" style="font-size: 4rem;"></i>
                                <p>وجّه الكاميرا لرؤية المنتج في غرفتك</p>
                            </div>
                        </div>
                        <div class="ar-controls">
                            <button class="orb-button">التقط صورة</button>
                        </div>
                    </div>
                `;
                
                arOverlay.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(5, 13, 26, 0.98);
                    z-index: 9999;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                `;
                
                document.body.appendChild(arOverlay);

                arOverlay.querySelector('.ar-close').addEventListener('click', () => {
                    arOverlay.remove();
                });
            });
        });
    }

    // ===== Product Comparison Drawer =====
    function initComparisonDrawer() {
        const compareButtons = document.querySelectorAll('[data-compare]');
        const comparisonItems = new Set();

        compareButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const productId = btn.dataset.productId;
                
                if (comparisonItems.has(productId)) {
                    comparisonItems.delete(productId);
                    btn.classList.remove('active');
                } else {
                    if (comparisonItems.size < 4) {
                        comparisonItems.add(productId);
                        btn.classList.add('active');
                    } else {
                        alert('يمكنك مقارنة 4 منتجات كحد أقصى');
                    }
                }

                updateComparisonBar();
            });
        });

        function updateComparisonBar() {
            // Update comparison bar UI
            console.log('Products to compare:', Array.from(comparisonItems));
        }
    }

    // ===== Video Background Control =====
    function initVideoBackground() {
        const videos = document.querySelectorAll('.hero-video-bg');
        
        videos.forEach(video => {
            // Pause when out of view
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        video.play();
                    } else {
                        video.pause();
                    }
                });
            });
            
            observer.observe(video);
        });
    }

    // ===== Add Custom Styles =====
    function addCustomStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .search-overlay-content {
                max-width: 800px;
                width: 90%;
                padding: 40px;
            }
            
            .search-close {
                position: absolute;
                top: 20px;
                left: 20px;
                background: none;
                border: none;
                font-size: 3rem;
                color: var(--bio-gold);
                cursor: pointer;
                opacity: 0.7;
                transition: opacity 0.3s ease;
            }
            
            .search-close:hover {
                opacity: 1;
            }
            
            .search-input-wrapper {
                display: flex;
                align-items: center;
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .search-input-wrapper i {
                font-size: 2rem;
                color: var(--bio-gold);
            }
            
            .search-input-wrapper input {
                flex: 1;
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                padding: 20px 30px;
                font-size: 1.5rem;
                color: var(--pearl-white);
                outline: none;
                transition: all 0.3s ease;
            }
            
            .search-input-wrapper input:focus {
                background: rgba(255, 255, 255, 0.08);
                border-color: var(--bio-gold);
                box-shadow: 0 0 30px rgba(212, 165, 116, 0.3);
            }
            
            .ar-viewer {
                width: 90%;
                max-width: 900px;
                max-height: 80vh;
                padding: 30px;
            }
            
            .ar-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }
            
            .ar-viewport {
                height: 500px;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-bottom: 20px;
            }
            
            .ar-placeholder {
                text-align: center;
                color: var(--pearl-gray);
            }
        `;
        document.head.appendChild(style);
    }

    // ===== Initialize All Effects =====
    function init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }

        console.log('🚀 Initializing Futuristic Theme Effects...');

        addCustomStyles();
        init3DParallax();
        initLayeredView();
        initInteractiveSliders();
        initCartDrawer();
        initSearchOrb();
        initFloatingCapsules();
        initTimelineProgress();
        initScrollReveal();
        initNavGlass();
        initCursorSpotlight();
        initARView();
        initComparisonDrawer();
        initVideoBackground();

        console.log('✅ Futuristic Theme Ready!');
    }

    init();

})();
