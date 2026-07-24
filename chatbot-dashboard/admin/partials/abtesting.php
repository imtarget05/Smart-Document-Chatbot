<?php
/**
 * A/B Testing — toggle retrieval variants on/off.
 *
 * Each row represents one variant. The toggle button sends a PUT request
 * to the REST API to update the active status.
 *
 * @package Chatbot_Dashboard
 */

defined( 'ABSPATH' ) || exit;

if ( ! current_user_can( 'manage_options' ) ) {
	wp_die( esc_html__( 'You do not have sufficient permissions.', 'chatbot-dashboard' ) );
}
?>
<div class="wrap chatbot-dashboard-wrap">
	<h1><?php echo esc_html__( 'A/B Testing Configuration', 'chatbot-dashboard' ); ?></h1>
	<p><?php esc_html_e( 'Enable or disable retrieval strategy variants. Disabled variants will not be assigned to new queries.', 'chatbot-dashboard' ); ?></p>

	<table class="wp-list-table widefat fixed striped">
		<thead>
			<tr>
				<th><?php esc_html_e( 'Variant', 'chatbot-dashboard' ); ?></th>
				<th><?php esc_html_e( 'Description', 'chatbot-dashboard' ); ?></th>
				<th><?php esc_html_e( 'Config', 'chatbot-dashboard' ); ?></th>
				<th><?php esc_html_e( 'Status', 'chatbot-dashboard' ); ?></th>
				<th><?php esc_html_e( 'Actions', 'chatbot-dashboard' ); ?></th>
			</tr>
		</thead>
		<tbody id="chatbot-ab-table">
			<tr><td colspan="5"><?php esc_html_e( 'Loading…', 'chatbot-dashboard' ); ?></td></tr>
		</tbody>
	</table>
</div>
