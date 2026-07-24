<?php
/**
 * Documents — paginated list of uploaded files with embedding status.
 *
 * @package Chatbot_Dashboard
 */

defined( 'ABSPATH' ) || exit;

if ( ! current_user_can( 'manage_options' ) ) {
	wp_die( esc_html__( 'You do not have sufficient permissions.', 'chatbot-dashboard' ) );
}
?>
<div class="wrap chatbot-dashboard-wrap">
	<h1><?php echo esc_html__( 'Documents', 'chatbot-dashboard' ); ?></h1>

	<table class="wp-list-table widefat fixed striped">
		<thead>
			<tr>
				<th><?php esc_html_e( 'File Name', 'chatbot-dashboard' ); ?></th>
				<th><?php esc_html_e( 'Type', 'chatbot-dashboard' ); ?></th>
				<th><?php esc_html_e( 'Size', 'chatbot-dashboard' ); ?></th>
				<th><?php esc_html_e( 'Chunks', 'chatbot-dashboard' ); ?></th>
				<th><?php esc_html_e( 'Embedding', 'chatbot-dashboard' ); ?></th>
				<th><?php esc_html_e( 'Uploaded', 'chatbot-dashboard' ); ?></th>
			</tr>
		</thead>
		<tbody id="chatbot-doc-table">
			<tr><td colspan="6"><?php esc_html_e( 'Loading…', 'chatbot-dashboard' ); ?></td></tr>
		</tbody>
	</table>

	<div id="chatbot-doc-pagination" class="chatbot-pagination"></div>
</div>
