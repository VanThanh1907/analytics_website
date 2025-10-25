// Tracking user interactions for analytics
(function() {
    'use strict';

    // Generate unique tab/window ID using sessionStorage (unique per tab)
    let tabId = sessionStorage.getItem('tabId');
    if (!tabId) {
        tabId = 'tab_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        sessionStorage.setItem('tabId', tabId);
    }
    console.log('Tab ID:', tabId);

    // Send heartbeat to keep session alive
    function sendHeartbeat() {
        fetch('/api/heartbeat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                tab_id: tabId,
                timestamp: new Date().toISOString()
            })
        }).catch(function(error) {
            console.log('Heartbeat error:', error);
        });
    }

    // Send initial heartbeat and then every 30 seconds
    sendHeartbeat();
    setInterval(sendHeartbeat, 30000);

    // Track page load time
    window.addEventListener('load', function() {
        trackEvent('page_load', {
            page: window.location.pathname,
            load_time: performance.now(),
            referrer: document.referrer
        });
    });

    // Track scroll depth
    let maxScrollDepth = 0;
    let scrollTimer;
    
    window.addEventListener('scroll', function() {
        clearTimeout(scrollTimer);
        scrollTimer = setTimeout(function() {
            const scrollDepth = Math.round((window.scrollY + window.innerHeight) / document.body.scrollHeight * 100);
            if (scrollDepth > maxScrollDepth) {
                maxScrollDepth = scrollDepth;
                trackEvent('scroll_depth', {
                    depth: scrollDepth,
                    page: window.location.pathname
                });
            }
        }, 250);
    });

    // Track product card clicks
    document.addEventListener('click', function(e) {
        const productCard = e.target.closest('.product-card');
        if (productCard) {
            const productId = productCard.getAttribute('data-product-id');
            const isRecommendation = productCard.classList.contains('recommended-product');
            
            trackEvent('product_card_click', {
                product_id: parseInt(productId),
                is_recommendation: isRecommendation,
                click_position: getElementPosition(productCard),
                page: window.location.pathname
            });
        }

        // Track product link clicks
        const productLink = e.target.closest('.product-link');
        if (productLink) {
            const productId = productLink.getAttribute('data-product-id');
            const productName = productLink.getAttribute('data-product-name');
            const source = productLink.getAttribute('data-source') || 'general';
            
            trackEvent('product_link_click', {
                product_id: parseInt(productId),
                product_name: productName,
                source: source,
                page: window.location.pathname
            });
        }

        // Track recommendation clicks specifically
        const recommendationClick = e.target.closest('.recommendation-click');
        if (recommendationClick) {
            const productId = recommendationClick.getAttribute('data-product-id');
            const productName = recommendationClick.getAttribute('data-product-name');
            
            trackEvent('recommendation_click', {
                product_id: parseInt(productId),
                product_name: productName,
                page: window.location.pathname
            });
        }
    });

    // Track search form submissions
    document.addEventListener('submit', function(e) {
        if (e.target.action && e.target.action.includes('/search')) {
            const searchInput = e.target.querySelector('input[name="q"]');
            if (searchInput) {
                trackEvent('search_submit', {
                    query: searchInput.value,
                    query_length: searchInput.value.length,
                    page: window.location.pathname
                });
            }
        }
    });

    // Track time spent on page
    let pageStartTime = Date.now();
    let isVisible = true;

    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            if (isVisible) {
                trackEvent('page_blur', {
                    time_spent: Date.now() - pageStartTime,
                    page: window.location.pathname
                });
                isVisible = false;
            }
        } else {
            if (!isVisible) {
                pageStartTime = Date.now();
                isVisible = true;
            }
        }
    });

    // Track when user leaves page
    window.addEventListener('beforeunload', function() {
        if (isVisible) {
            trackEvent('page_unload', {
                time_spent: Date.now() - pageStartTime,
                page: window.location.pathname
            });
        }
    });

    // Mouse tracking for heat maps (sample every 2 seconds when moving)
    let mouseTimer;
    let lastMouseEvent = null;

    document.addEventListener('mousemove', function(e) {
        clearTimeout(mouseTimer);
        lastMouseEvent = {
            x: e.clientX,
            y: e.clientY,
            timestamp: Date.now()
        };

        mouseTimer = setTimeout(function() {
            if (lastMouseEvent) {
                trackEvent('mouse_position', {
                    x: lastMouseEvent.x,
                    y: lastMouseEvent.y,
                    viewport_width: window.innerWidth,
                    viewport_height: window.innerHeight,
                    page: window.location.pathname
                });
                lastMouseEvent = null;
            }
        }, 2000);
    });

    // Helper functions
    function trackEvent(eventType, data) {
        // Only track if user is authenticated (to respect privacy)
        if (!document.body.dataset.userAuthenticated) {
            return;
        }

        fetch('/api/track_click', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                event_type: eventType,
                data: data,
                timestamp: new Date().toISOString(),
                user_agent: navigator.userAgent,
                screen_resolution: screen.width + 'x' + screen.height
            })
        }).catch(function(error) {
            console.log('Tracking error:', error);
        });
    }

    function getElementPosition(element) {
        const rect = element.getBoundingClientRect();
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
        
        return {
            top: rect.top + scrollTop,
            left: rect.left + scrollLeft,
            width: rect.width,
            height: rect.height
        };
    }

    // Global function for manual tracking (legacy support)
    window.trackClick = function(action, productId, productName, additionalData) {
        trackEvent('manual_click', {
            action: action,
            product_id: productId,
            product_name: productName,
            page: window.location.pathname,
            ...additionalData
        });
    };

    // Handle action buttons (new method)
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('action-btn')) {
            const action = e.target.getAttribute('data-action');
            const productId = parseInt(e.target.getAttribute('data-product-id'));
            const productName = e.target.getAttribute('data-product-name');
            
            trackEvent('action_button_click', {
                action: action,
                product_id: productId,
                product_name: productName,
                page: window.location.pathname
            });
        }
    });

    // Add user authentication status to body for tracking
    if (typeof currentUserId !== 'undefined' && currentUserId) {
        document.body.dataset.userAuthenticated = 'true';
    }

})();