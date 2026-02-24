/**
 * Tony Store - Futuristic Interactive Effects
 * التأثيرات التفاعلية المستقبلية
 */

document.addEventListener('DOMContentLoaded', function() {
    // ========== Header Transformation on Scroll ==========
    const header = document.querySelector('.main-header, .store-header, .header-futuristic, header');
    let lastScroll = 0;
    
    if (header) {
        window.addEventListener('scroll', function() {
            const currentScroll = window.pageYOffset;
            
            if (currentScroll > 100) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
            
            lastScroll = currentScroll;
        });
    }
    
    // ========== Animate Elements on Scroll ==========
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-on-scroll');
            }
        });
    }, observerOptions);
    
    // Observe product cards
    document.querySelectorAll('.product-card, .glass-card, .cart-item').forEach(card => {
        observer.observe(card);
    });
    
    // ========== Button Ripple Effect ==========
    function createRipple(event) {
        const button = event.currentTarget;
        
        // Only apply on buttons with certain classes
        if (!button.classList.contains('btn-primary') && 
            !button.classList.contains('btn-futuristic')) {
            return;
        }
        
        const ripple = document.createElement('span');
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple');
        
        // Add styles for ripple
        ripple.style.position = 'absolute';
        ripple.style.borderRadius = '50%';
        ripple.style.background = 'rgba(255, 255, 255, 0.3)';
        ripple.style.transform = 'scale(0)';
        ripple.style.animation = 'ripple-animation 0.6s ease-out';
        ripple.style.pointerEvents = 'none';
        
        button.appendChild(ripple);
        
        setTimeout(() => {
            ripple.remove();
        }, 600);
    }
    
    // Add ripple animation CSS
    if (!document.querySelector('#ripple-animation-style')) {
        const style = document.createElement('style');
        style.id = 'ripple-animation-style';
        style.textContent = `
            @keyframes ripple-animation {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Attach ripple to buttons
    document.querySelectorAll('.btn-primary, .btn-futuristic').forEach(button => {
        button.style.position = 'relative';
        button.style.overflow = 'hidden';
        button.addEventListener('click', createRipple);
    });
    
    // ========== Smooth Scroll for Anchor Links ==========
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#' && href !== '#!') {
                const target = document.querySelector(href);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });
    
    // ========== Floating Product Images ==========
    document.querySelectorAll('.product-card img').forEach((img, index) => {
        img.style.animationDelay = `${index * 0.1}s`;
    });
    
    // ========== Golden Glow on Input Focus ==========
    document.querySelectorAll('input, textarea, select').forEach(input => {
        input.addEventListener('focus', function() {
            this.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        });
    });
    
    // ========== Product Card Interactive Tilt Effect ==========
    document.querySelectorAll('.product-card').forEach(card => {
        card.addEventListener('mousemove', function(e) {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            const rotateX = (y - centerY) / 20;
            const rotateY = (centerX - x) / 20;
            
            card.style.transform = `
                perspective(1000px)
                rotateX(${rotateX}deg)
                rotateY(${rotateY}deg)
                translateY(-12px)
                scale(1.02)
            `;
        });
        
        card.addEventListener('mouseleave', function() {
            card.style.transform = '';
        });
    });
    
    // ========== Add Golden Particle Effect on Button Hover ==========
    function createParticle(x, y) {
        const particle = document.createElement('div');
        particle.style.position = 'fixed';
        particle.style.left = x + 'px';
        particle.style.top = y + 'px';
        particle.style.width = '4px';
        particle.style.height = '4px';
        particle.style.borderRadius = '50%';
        particle.style.background = '#D4AF37';
        particle.style.boxShadow = '0 0 10px rgba(212, 175, 55, 0.8)';
        particle.style.pointerEvents = 'none';
        particle.style.zIndex = '9999';
        particle.style.animation = 'particle-float 1s ease-out forwards';
        
        document.body.appendChild(particle);
        
        setTimeout(() => {
            particle.remove();
        }, 1000);
    }
    
    // Add particle animation CSS
    if (!document.querySelector('#particle-animation-style')) {
        const style = document.createElement('style');
        style.id = 'particle-animation-style';
        style.textContent = `
            @keyframes particle-float {
                to {
                    transform: translateY(-100px);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Add particles on button hover
    document.querySelectorAll('.btn-primary, .btn-futuristic').forEach(button => {
        button.addEventListener('mouseenter', function(e) {
            const rect = this.getBoundingClientRect();
            for (let i = 0; i < 3; i++) {
                setTimeout(() => {
                    createParticle(
                        rect.left + Math.random() * rect.width,
                        rect.top + Math.random() * rect.height
                    );
                }, i * 100);
            }
        });
    });
    
    // ========== Parallax Background Effect ==========
    window.addEventListener('scroll', function() {
        const scrolled = window.pageYOffset;
        const parallaxElements = document.querySelectorAll('.hero-section, .glass-card');
        
        parallaxElements.forEach(element => {
            const speed = 0.5;
            const yPos = -(scrolled * speed);
            element.style.backgroundPosition = `center ${yPos}px`;
        });
    });
    
    // ========== Add Loading Animation for Images ==========
    document.querySelectorAll('img').forEach(img => {
        if (!img.complete) {
            img.style.opacity = '0';
            img.style.transform = 'scale(0.9)';
            
            img.addEventListener('load', function() {
                this.style.transition = 'all 0.5s ease';
                this.style.opacity = '1';
                this.style.transform = 'scale(1)';
            });
        }
    });
    
    // ========== Cart Badge Pulse Effect ==========
    const cartBadge = document.querySelector('.badge');
    if (cartBadge) {
        cartBadge.classList.add('pulse-effect');
    }
    
    // ========== Golden Trail Cursor Effect (Optional - Subtle) ==========
    let trailTimeout;
    document.addEventListener('mousemove', function(e) {
        clearTimeout(trailTimeout);
        trailTimeout = setTimeout(() => {
            const trail = document.createElement('div');
            trail.style.position = 'fixed';
            trail.style.left = e.clientX + 'px';
            trail.style.top = e.clientY + 'px';
            trail.style.width = '2px';
            trail.style.height = '2px';
            trail.style.borderRadius = '50%';
            trail.style.background = 'rgba(212, 175, 55, 0.3)';
            trail.style.pointerEvents = 'none';
            trail.style.zIndex = '9999';
            trail.style.animation = 'trail-fade 0.5s ease-out forwards';
            
            document.body.appendChild(trail);
            
            setTimeout(() => {
                trail.remove();
            }, 500);
        }, 50);
    });
    
    // Add trail animation CSS
    if (!document.querySelector('#trail-animation-style')) {
        const style = document.createElement('style');
        style.id = 'trail-animation-style';
        style.textContent = `
            @keyframes trail-fade {
                to {
                    transform: scale(10);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    console.log('✨ Futuristic Effects Initialized - التأثيرات المستقبلية مفعلة');
});
