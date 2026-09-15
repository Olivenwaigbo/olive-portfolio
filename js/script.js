/* =========================================================
   OLIVE CHIKA NWAIGBO
   PORTFOLIO INTERACTIONS
========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    /* =====================================================
       1. REDUCED MOTION CHECK
    ===================================================== */

    const prefersReducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;


    /* =====================================================
       2. SCROLL REVEAL
    ===================================================== */

    const revealElements = document.querySelectorAll(
        ".section-heading, " +
        ".about-grid, " +
        ".experience-item, " +
        ".process-step, " +
        ".industry-card, " +
        ".project-card, " +
        ".featured-certification, " +
        ".certificate-card, " +
        ".capability, " +
        ".contact-card"
    );


    revealElements.forEach((element) => {

        element.classList.add("scroll-reveal");

    });


    /*
       If the visitor prefers reduced motion,
       show everything immediately.
    */

    if (prefersReducedMotion) {

        revealElements.forEach((element) => {

            element.classList.add("is-visible");

        });

    } else {

        const revealObserver = new IntersectionObserver(
            (entries, observer) => {

                entries.forEach((entry) => {

                    if (!entry.isIntersecting) return;

                    entry.target.classList.add("is-visible");

                    observer.unobserve(entry.target);

                });

            },
            {
                threshold: 0.12
            }
        );


        revealElements.forEach((element) => {

            revealObserver.observe(element);

        });

    }


    /* =====================================================
       3. STAGGERED CARD REVEALS
    ===================================================== */

    const cardGroups = [
        ".industry-grid",
        ".project-grid",
        ".certificate-grid",
        ".capabilities-grid"
    ];


    cardGroups.forEach((selector) => {

        const group = document.querySelector(selector);

        if (!group) return;

        const cards = group.children;


        Array.from(cards).forEach((card, index) => {

            card.style.setProperty(
                "--reveal-delay",
                `${index * 100}ms`
            );

        });

    });


    /* =====================================================
       4. HERO MOUSE PARALLAX
    ===================================================== */

    const hero = document.querySelector(".hero");
    const exploration =
        document.querySelector(".exploration-visual");


    if (
        hero &&
        exploration &&
        window.innerWidth > 900 &&
        !prefersReducedMotion
    ) {

        hero.addEventListener("mousemove", (event) => {

            const rect =
                hero.getBoundingClientRect();


            const x =
                (event.clientX - rect.left) /
                rect.width -
                0.5;


            const y =
                (event.clientY - rect.top) /
                rect.height -
                0.5;


            exploration.style.transform =
                `translate(${x * 12}px, ${y * 12}px)`;

        });


        hero.addEventListener("mouseleave", () => {

            exploration.style.transform =
                "translate(0, 0)";

        });

    }


    /* =====================================================
       5. STAT NUMBER REVEAL
    ===================================================== */

    const statCards =
        document.querySelectorAll(".stat-card");


    if (prefersReducedMotion) {

        statCards.forEach((card) => {

            const strong =
                card.querySelector("strong");

            if (strong) {

                strong.classList.add("stat-active");

            }

        });

    } else {

        const statsObserver =
            new IntersectionObserver(
                (entries, observer) => {

                    entries.forEach((entry) => {

                        if (!entry.isIntersecting) return;


                        const strong =
                            entry.target.querySelector("strong");


                        if (strong) {

                            strong.classList.add(
                                "stat-active"
                            );

                        }


                        observer.unobserve(
                            entry.target
                        );

                    });

                },
                {
                    threshold: 0.5
                }
            );


        statCards.forEach((card) => {

            statsObserver.observe(card);

        });

    }


    /* =====================================================
       6. PROCESS LINE ANIMATION
    ===================================================== */

    const processSection =
        document.querySelector(".process-section");


    if (processSection) {

        if (prefersReducedMotion) {

            processSection.classList.add(
                "process-active"
            );

        } else {

            const processObserver =
                new IntersectionObserver(
                    (entries, observer) => {

                        entries.forEach((entry) => {

                            if (!entry.isIntersecting) {
                                return;
                            }


                            processSection.classList.add(
                                "process-active"
                            );


                            observer.unobserve(
                                processSection
                            );

                        });

                    },
                    {
                        threshold: 0.25
                    }
                );


            processObserver.observe(
                processSection
            );

        }

    }


    /* =====================================================
       7. PROJECT CARD INTERACTION
    ===================================================== */

    const projectCards =
        document.querySelectorAll(".project-card");


    if (!prefersReducedMotion) {

        projectCards.forEach((card) => {

            card.addEventListener(
                "mouseenter",
                () => {

                    card.classList.add(
                        "project-active"
                    );

                }
            );


            card.addEventListener(
                "mouseleave",
                () => {

                    card.classList.remove(
                        "project-active"
                    );

                }
            );

        });

    }


    /* =====================================================
       8. INDUSTRY CARD INTERACTION
    ===================================================== */

    const industryCards =
        document.querySelectorAll(".industry-card");


    if (!prefersReducedMotion) {

        industryCards.forEach((card) => {

            const symbol =
                card.querySelector(
                    ".industry-symbol"
                );


            if (!symbol) return;


            card.addEventListener(
                "mouseenter",
                () => {

                    symbol.classList.add(
                        "symbol-active"
                    );

                }
            );


            card.addEventListener(
                "mouseleave",
                () => {

                    symbol.classList.remove(
                        "symbol-active"
                    );

                }
            );

        });

    }


    /* =====================================================
       9. SMOOTH NAVIGATION
    ===================================================== */

    document.querySelectorAll(
        'a[href^="#"]'
    ).forEach((link) => {

        link.addEventListener(
            "click",
            (event) => {

                const targetId =
                    link.getAttribute("href");


                if (
                    !targetId ||
                    targetId === "#"
                ) {
                    return;
                }


                const target =
                    document.querySelector(
                        targetId
                    );


                if (!target) return;


                event.preventDefault();


                target.scrollIntoView({

                    behavior:
                        prefersReducedMotion
                            ? "auto"
                            : "smooth",

                    block: "start"

                });

            }
        );

    });


    /* =====================================================
       10. LAB PLANE INTERACTION
    ===================================================== */

    const labPlane =
        document.querySelector(".lab-plane");


    if (
        labPlane &&
        !prefersReducedMotion
    ) {

        labPlane.addEventListener(
            "mouseenter",
            () => {

                labPlane.classList.add(
                    "plane-active"
                );

            }
        );


        labPlane.addEventListener(
            "mouseleave",
            () => {

                labPlane.classList.remove(
                    "plane-active"
                );

            }
        );

    }


    /* =====================================================
       11. CONTACT GLOW
    ===================================================== */

    const contactCard =
        document.querySelector(".contact-card");


    if (
        contactCard &&
        window.innerWidth > 900 &&
        !prefersReducedMotion
    ) {

        contactCard.addEventListener(
            "mousemove",
            (event) => {

                const rect =
                    contactCard.getBoundingClientRect();


                const x =
                    ((event.clientX - rect.left) /
                        rect.width) *
                    100;


                const y =
                    ((event.clientY - rect.top) /
                        rect.height) *
                    100;


                contactCard.style.setProperty(
                    "--mouse-x",
                    `${x}%`
                );


                contactCard.style.setProperty(
                    "--mouse-y",
                    `${y}%`
                );

            }
        );


        contactCard.addEventListener(
            "mouseleave",
            () => {

                contactCard.style.setProperty(
                    "--mouse-x",
                    "50%"
                );


                contactCard.style.setProperty(
                    "--mouse-y",
                    "50%"
                );

            }
        );

    }


    /* =====================================================
       12. HERO BACKGROUND MOUSE RESPONSE
    ===================================================== */

    const heroGlowOne =
        document.querySelector(
            ".hero-background-one"
        );

    const heroGlowTwo =
        document.querySelector(
            ".hero-background-two"
        );


    if (
        hero &&
        heroGlowOne &&
        heroGlowTwo &&
        window.innerWidth > 900 &&
        !prefersReducedMotion
    ) {

        hero.addEventListener(
            "mousemove",
            (event) => {

                const rect =
                    hero.getBoundingClientRect();


                const x =
                    (event.clientX - rect.left) /
                    rect.width -
                    0.5;


                const y =
                    (event.clientY - rect.top) /
                    rect.height -
                    0.5;


                heroGlowOne.style.transform =
                    `translate(${x * 18}px, ${y * 18}px) scale(1.05)`;


                heroGlowTwo.style.transform =
                    `translate(${x * -12}px, ${y * -12}px) scale(1.05)`;

            }
        );


        hero.addEventListener(
            "mouseleave",
            () => {

                heroGlowOne.style.transform =
                    "translate(0, 0) scale(1)";


                heroGlowTwo.style.transform =
                    "translate(0, 0) scale(1)";

            }
        );

    }


    /* =====================================================
       13. BUTTON MICRO-INTERACTION
    ===================================================== */

    if (!prefersReducedMotion) {

        const buttons =
            document.querySelectorAll(
                ".button, .nav-button"
            );


        buttons.forEach((button) => {

            button.addEventListener(
                "mouseenter",
                () => {

                    button.style.setProperty(
                        "--button-scale",
                        "1.02"
                    );

                }
            );


            button.addEventListener(
                "mouseleave",
                () => {

                    button.style.setProperty(
                        "--button-scale",
                        "1"
                    );

                }
            );

        });

    }

});