odoo.define("dash_backend_theme.SidebarMenu", [], function (require) {
    "use strict";

    const { ensureJQuery } = require("@web/core/ensure_jquery");

    // Handle collapse functionality
    function handleCollapse(collapse) {
        if (collapse._isShown()) {
            collapse.hide();
        }
    }

    // Handle media query response for apps toggle
    function handleAppsToggleMedia(mediaQuery) {
        if (mediaQuery.matches) {
            $(".sidebar").toggleClass("show");
        } else {
            $(".sidebar").toggleClass("active");
            $(".o_action_manager").toggleClass("active");
            $(".apps_toggle").toggleClass("active");

            if ($(".sidebar").hasClass("active")) {
                window.collapseList.forEach(handleCollapse);
            }
        }
    }

    // Handle large screen width adjustments
    function handleLargeScreen() {
        const e = window.matchMedia("(min-width: 1600px)");
        if (e.matches) {
            setTimeout(() => {
                const currentWidth = $(".o_form_sheet_bg").width();
                $(".o_control_panel").width(currentWidth + 66);
                $(".o_content").css("background", "unset");
            }, 300);
        } else {
            $(".o_control_panel").css("width", "initial");
        }
    }

    // Track shown collapses
    function trackShownCollapses() {
        const shownCollapses = [];
        window.collapseList.forEach((collapse) => {
            if (collapse._isShown() && shownCollapses.indexOf(collapse) === -1) {
                shownCollapses.push(collapse);
            }
        });
        return shownCollapses;
    }

    // Setup collapse elements
    function setupCollapses() {
        const collapseElements = document.querySelectorAll(".collapse");
        const collapseList = [...collapseElements].map(
            (collapseEl) => new Collapse(collapseEl, { toggle: false })
        );
        window.collapseList = collapseList;

        // Setup event listeners
        collapseElements.forEach((element) => {
            element.addEventListener("shown.bs.collapse", () => {
                // Initialize with existing shown collapses before updating
                window.collapseShowns = trackShownCollapses();
            });
        });
    }

    ensureJQuery().then(() => {
        // Explicitly declare collapseShowns as a global variable
        window.collapseShowns = [];

        // Apps toggle click event
        $(document).on("click", ".apps_toggle", function () {
            const mediaQuery = window.matchMedia("(max-width: 575.98px)");
            handleAppsToggleMedia(mediaQuery);
            handleLargeScreen();
        });

        // Sidebar click event
        $(document).on("click", ".sidebar", function (event) {
            const mediaQuery = window.matchMedia("(max-width: 575.98px)");
            if (event.offsetX > 250 && mediaQuery.matches) {
                $(".sidebar").toggleClass("show");
            }
        });

        // Sidebar link click event
        $(document).on("click", ".sidebar a", function () {
            const menu = $(".sidebar a");
            const $this = $(this);

            menu.removeClass("active");
            $this.addClass("active");
        });

        // Sidebar mouseenter event
        $(document).on("mouseenter", ".sidebar", function () {
            if ($(".apps_toggle").hasClass("active")) {
                // Use the global collapseShowns variable
                window.collapseShowns.forEach((collapse) => {
                    collapse.show();
                });
            }
        });

        // Sidebar mouseleave event
        $(document).on("mouseleave", ".sidebar", function () {
            if ($(".apps_toggle").hasClass("active")) {
                // Use the global collapseShowns variable
                window.collapseShowns.forEach((collapse) => collapse.hide());
            }
        });

        // Child menus click event
        $(document).on("click", ".child_menus", function () {
            const mediaQuery = window.matchMedia("(max-width: 575.98px)");
            if (mediaQuery.matches) {
                setTimeout(() => {
                    $(".sidebar").toggleClass("show");
                }, 200);
            }
        });

        // Parent menu click event
        $(document).on("click", ".sidebar_panel .sidebar .sidebar_menu .parentmenu a", function () {
            if ($(".apps_toggle").is(":visible")) {
                $(".sidebar_menu").toggleClass("active");
                $(".apps_toggle").toggleClass("active");
            }
        });

        // Header sub-menus click event
        $(document).on("click", ".header-sub-menus .nav-item a", function () {
            const allMenus = $(".nav-link");
            allMenus.removeClass("active");

            const parent = this.closest(".header-sub-menus");
            const currMenu = parent.previousElementSibling;
            $(currMenu).addClass("active");
        });

        // Initialize when document is ready
        $(document).ready(setupCollapses);
    });
});
