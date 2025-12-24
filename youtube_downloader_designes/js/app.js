/**
 * VidFetch Mock Application Logic
 */

const App = {
    state: {
        currentView: 'home',
        downloads: [
            {
                id: 1,
                title: "Lo-Fi Beats to Study/Relax To - 24/7 Radio",
                format: "MP3 • 128kbps",
                progress: 100,
                status: 'completed',
                thumbnail: "https://lh3.googleusercontent.com/aida-public/AB6AXuAo-dpBtgRFS2rU23k2RoHQmQrIpC9RN3i3_K4T4g-X3GFz6Ux5JLjaFhG0AyRol7UALsJXLVE77Pui5HW3x5RYLUJIDTPJ10eQmn5w2PUy9nKMLtTvStFWX-yb6huIhrkr7-RegbmpWtJRikdP8dh-Aoc4OFXmuwlL4T4u_nZVDX7vKWIpAavCCH1ymPh8ue8rbGlCNFpb4g8mNVoFu5_C30mVOZuP44HGaAjk9PnDV5caXRVvvex_NWseXb0u7rGjTfBnHYEAgSPU"
            },
            {
                id: 2,
                title: "Top 10 Modern UI Design Trends 2024",
                format: "MP4 • 1080p",
                progress: 100,
                status: 'completed',
                thumbnail: "https://lh3.googleusercontent.com/aida-public/AB6AXuA7knpUlwehr2VuInzYKdxjbld_3jAviKmK7gcVyvgcqn5JvwWHrzAzfXtzf63-VsXpTOe2dwgMHstLj2vQ1LsoGnlyD9XB7vvnafBQ-pDCaEGAUw3BQ2wK59vAFXWbvH4jZ_YkYrlMwmvrfwGgzufqedeJL2qKoPvpRKFrgs1VHB1ejfk7fQQ4za3sbze8XzjCt5rn5gXqG9B_rRzNftj7I6xl33SbSUg5btv_ZUf5uOjNwx8Np73mkGvzR4T_J_RxmX2cGlI_9tSn"
            },
            {
                id: 3,
                title: "Understanding Quantum Computing",
                format: "MP4 • 4K",
                progress: 45,
                status: 'active',
                thumbnail: "https://lh3.googleusercontent.com/aida-public/AB6AXuA7knpUlwehr2VuInzYKdxjbld_3jAviKmK7gcVyvgcqn5JvwWHrzAzfXtzf63-VsXpTOe2dwgMHstLj2vQ1LsoGnlyD9XB7vvnafBQ-pDCaEGAUw3BQ2wK59vAFXWbvH4jZ_YkYrlMwmvrfwGgzufqedeJL2qKoPvpRKFrgs1VHB1ejfk7fQQ4za3sbze8XzjCt5rn5gXqG9B_rRzNftj7I6xl33SbSUg5btv_ZUf5uOjNwx8Np73mkGvzR4T_J_RxmX2cGlI_9tSn"
            }
        ]
    },

    init() {
        this.bindEvents();
        this.router();
        window.addEventListener('hashchange', () => this.router());
    },

    bindEvents() {
        // Global clicks for navigation if needed, mostly handled by <a> tags with href="#..."

        // Settings Modal Triggers
        document.querySelectorAll('[data-trigger="settings"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleModal('settings-modal', true);
            });
        });

        // Close Modals
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) this.toggleModal(modal.id, false);
            });
        });
    },

    router() {
        const hash = window.location.hash.slice(1) || 'home';

        // Mock Loading State logic for Search
        if (hash === 'searching') {
            this.showLoading(true);
            setTimeout(() => {
                this.showLoading(false);
                window.location.hash = '#results';
            }, 1500);
            return;
        }

        this.renderView(hash);
    },

    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            if (show) overlay.classList.remove('hidden');
            else overlay.classList.add('hidden');
        }
    },

    renderView(viewName) {
        // Hide all views
        document.querySelectorAll('.view-section').forEach(el => {
            el.classList.add('hidden');
            el.classList.remove('fade-in');
        });

        // Show target view
        const target = document.getElementById(`view-${viewName}`);
        if (target) {
            target.classList.remove('hidden');
            target.classList.add('fade-in');
            this.state.currentView = viewName;

            this.state.currentView = viewName;


            // Trigger specific view logic
            if (viewName === 'downloads') this.renderDownloads();
        } else {
            // 404 fallback to home
            if (window.location.hash !== '') window.location.hash = '#home';
        }
    },

    toggleModal(modalId, show) {
        const modal = document.getElementById(modalId);
        if (show) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
        } else {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        }
    },

    // Mock Business Logic
    renderDownloads() {
        // In a real app, this would re-render the table based on this.state.downloads
        // For this mock, we just ensure the view is shown. 
        // We could implement a simple render loop here if needed.
        console.log("Rendering downloads...", this.state.downloads);
    },

    startMockDownload() {
        // Simulate "Starting..." feedback
        const btn = document.activeElement;
        if (btn) {
            const originalText = btn.innerHTML;
            btn.innerHTML = `<span class="material-symbols-outlined animate-spin">sync</span> Starting...`;
            setTimeout(() => {
                btn.innerHTML = originalText;
                // Navigate to downloads
                window.location.hash = '#downloads';

                // Optional: Show a toast?
            }, 800);
        }
    },

    toggleResultsMode() {
        const single = document.getElementById('result-single');
        const playlist = document.getElementById('result-playlist');

        if (single && playlist) {
            if (single.classList.contains('hidden')) {
                // Show single, hide playlist
                single.classList.remove('hidden');
                playlist.classList.add('hidden');
            } else {
                // Show playlist, hide single
                single.classList.add('hidden');
                playlist.classList.remove('hidden');
            }
        }
    },

    toggleSelectAll(btn) {
        const checkboxes = document.querySelectorAll('.playlist-checkbox');
        const isSelectAll = btn.innerText === 'Select All';

        checkboxes.forEach(cb => cb.checked = isSelectAll);

        btn.innerText = isSelectAll ? 'Deselect All' : 'Select All';

        this.updateSelectionCount();
    },

    updateSelectionCount() {
        const count = document.querySelectorAll('.playlist-checkbox:checked').length;
        const btn = document.getElementById('btn-download-selected');
        if (btn) {
            const span = btn.querySelector('span:not(.material-symbols-outlined)');
            if (span) span.innerText = `Download Selected (${count})`;

            // Optional: Disable button if 0
            if (count === 0) {
                btn.classList.add('opacity-50', 'pointer-events-none');
            } else {
                btn.classList.remove('opacity-50', 'pointer-events-none');
            }
        }
    }
};

document.addEventListener('DOMContentLoaded', () => App.init());
