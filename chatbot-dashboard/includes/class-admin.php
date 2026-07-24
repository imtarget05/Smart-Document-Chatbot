<?php
/**
 * Admin — registers wp-admin menu pages and enqueues assets.
 *
 * Each sub-menu page renders via a dedicated template file so that markup
 * is kept separate from business logic.
 *
 * @package Chatbot_Dashboard
 */

namespace Chatbot_Dashboard;

defined( 'ABSPATH' ) || exit;

class Admin {

	/**
	 * Hook into WordPress admin.
	 */
	public function init(): void {
		add_action( 'admin_menu', array( $this, 'register_menu' ) );
		add_action( 'admin_enqueue_scripts', array( $this, 'enqueue_assets' ) );
	}

	/**
	 * Register the top-level menu and sub-menus.
	 *
	 * capability check happens here — only users with manage_options
	 * (admins) see any of these pages.
	 */
	public function register_menu(): void {
		add_menu_page(
			__( 'Chatbot Dashboard', 'chatbot-dashboard' ),
			__( 'Chatbot Dashboard', 'chatbot-dashboard' ),
			'manage_options',
			'chatbot-dashboard',
			array( $this, 'render_overview' ),
			'dashicons-analytics',
			30
		);

		add_submenu_page(
			'chatbot-dashboard',
			__( 'Overview', 'chatbot-dashboard' ),
			__( 'Overview', 'chatbot-dashboard' ),
			'manage_options',
			'chatbot-dashboard',
			array( $this, 'render_overview' )
		);

		add_submenu_page(
			'chatbot-dashboard',
			__( 'Conversations', 'chatbot-dashboard' ),
			__( 'Conversations', 'chatbot-dashboard' ),
			'manage_options',
			'chatbot-dashboard-conversations',
			array( $this, 'render_conversations' )
		);

		add_submenu_page(
			'chatbot-dashboard',
			__( 'Documents', 'chatbot-dashboard' ),
			__( 'Documents', 'chatbot-dashboard' ),
			'manage_options',
			'chatbot-dashboard-documents',
			array( $this, 'render_documents' )
		);

		add_submenu_page(
			'chatbot-dashboard',
			__( 'A/B Testing', 'chatbot-dashboard' ),
			__( 'A/B Testing', 'chatbot-dashboard' ),
			'manage_options',
			'chatbot-dashboard-abtesting',
			array( $this, 'render_abtesting' )
		);
	}

	/**
	 * Enqueue JS/CSS only on our plugin pages.
	 *
	 * @param string $hook Current admin page hook.
	 */
	public function enqueue_assets( string $hook ): void {
		if ( 0 !== strpos( $hook, 'chatbot-dashboard' ) ) {
			return;
		}

		wp_enqueue_style(
			'chatbot-dashboard-admin',
			CHATBOT_DASHBOARD_URL . 'assets/css/dashboard.css',
			array(),
			CHATBOT_DASHBOARD_VERSION
		);

		wp_enqueue_script(
			'chatbot-dashboard-admin',
			CHATBOT_DASHBOARD_URL . 'assets/js/dashboard.js',
			array( 'wp-api-fetch' ),
			CHATBOT_DASHBOARD_VERSION,
			true
		);

		wp_localize_script(
			'chatbot-dashboard-admin',
			'chatbotDashboard',
			array(
				'root'  => esc_url_raw( rest_url( 'chatbot-dashboard/v1' ) ),
				'nonce' => wp_create_nonce( 'wp_rest' ),
			)
		);
	}

	// ── Render methods ───────────────────────────────────────────────────

	public function render_overview(): void {
		$this->render_template( 'overview' );
	}

	public function render_conversations(): void {
		$this->render_template( 'conversations' );
	}

	public function render_documents(): void {
		$this->render_template( 'documents' );
	}

	public function render_abtesting(): void {
		if ( ! current_user_can( 'manage_options' ) ) {
			wp_die( esc_html__( 'You do not have sufficient permissions.', 'chatbot-dashboard' ) );
		}
		$this->render_template( 'abtesting' );
	}

	/**
	 * Include a template file from admin/partials/.
	 *
	 * @param string $slug Template slug (without .php).
	 */
	private function render_template( string $slug ): void {
		$path = CHATBOT_DASHBOARD_DIR . 'admin/partials/' . $slug . '.php';
		if ( file_exists( $path ) ) {
			include $path;
		} else {
			echo '<div class="notice notice-warning"><p>' . esc_html__( 'Template not found.', 'chatbot-dashboard' ) . '</p></div>';
		}
	}
}
