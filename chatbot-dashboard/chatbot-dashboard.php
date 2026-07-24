<?php
/**
 * Plugin Name:     Chatbot Dashboard
 * Plugin URI:      https://example.com/chatbot-dashboard
 * Description:     Admin dashboard for monitoring Smart Document Chatbot — conversation logs,
 *                  document ingestion, A/B testing config, and real-time stats.
 * Version:         1.0.0
 * Requires PHP:    7.4
 * Requires at least: 5.7
 * Author:          Smart Document Chatbot Team
 * Text Domain:     chatbot-dashboard
 * Domain Path:     /languages
 *
 * @package Chatbot_Dashboard
 */

defined( 'ABSPATH' ) || exit;

define( 'CHATBOT_DASHBOARD_VERSION', '1.0.0' );
define( 'CHATBOT_DASHBOARD_FILE', __FILE__ );
define( 'CHATBOT_DASHBOARD_DIR', plugin_dir_path( __FILE__ ) );
define( 'CHATBOT_DASHBOARD_URL', plugin_dir_url( __FILE__ ) );

/**
 * PSR-4-like autoloader for the Chatbot_Dashboard namespace.
 *
 * Maps Chatbot_Dashboard\Class_Name to includes/class-class-name.php.
 */
spl_autoload_register(
	function ( $class ) {
		$prefix = 'Chatbot_Dashboard\\';
		if ( 0 !== strncmp( $class, $prefix, strlen( $prefix ) ) ) {
			return;
		}
		$relative = substr( $class, strlen( $prefix ) );
		$file     = strtolower( str_replace( '_', '-', $relative ) );
		$path     = CHATBOT_DASHBOARD_DIR . 'includes/class-' . $file . '.php';
		if ( file_exists( $path ) ) {
			require $path;
		}
	}
);

/**
 * Fires on plugin activation — creates custom tables and seeds demo data.
 */
register_activation_hook(
	CHATBOT_DASHBOARD_FILE,
	array( 'Chatbot_Dashboard\\Activator', 'activate' )
);

/**
 * Bootstrap the admin UI and REST routes.
 */
if ( is_admin() ) {
	$admin  = new Chatbot_Dashboard\Admin();
	$admin->init();
}

$rest = new Chatbot_Dashboard\Rest_Controller();
$rest->init();
