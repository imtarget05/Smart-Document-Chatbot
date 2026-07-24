<?php
/**
 * Conversations — paginated log table with intent/status filters.
 *
 * @package Chatbot_Dashboard
 */

defined( 'ABSPATH' ) || exit;

if ( ! current_user_can( 'manage_options' ) ) {
	wp_die( esc_html__( 'You do not have sufficient permissions.', 'chatbot-dashboard' ) );
}
?>
<div class="wrap chatbot-dashboard-wrap">
	<h1><?php echo esc_html__( 'Conversations', 'chatbot-dashboard' ); ?></h1>

	<div class="chatbot-filters">
		<label for="filter-intent"><?php esc_html_e( 'Intent:', 'chatbot-dashboard' ); ?></label>
		<select id="filter-intent">
			<option value=""><?php esc_html_e( 'All', 'chatbot-dashboard' ); ?></option>
			<option value="rag">rag</option>
			<option value="report">report</option>
			<option value="compare">compare</option>
			<option value="research">research</option>
			<option value="action">action</option>
		</select>

		<label for="filter-status"><?php esc_html_e( 'Status:', 'chatbot-dashboard' ); ?></label>
		<select id="filter-status">
			<option value=""><?php esc_html_e( 'All', 'chatbot-dashboard' ); ?></option>
			<option value="success"><?php esc_html_e( 'Success', 'chatbot-dashboard' ); ?></option>
			<option value="error"><?php esc_html_e( 'Error', 'chatbot-dashboard' ); ?></option>
		</select>

		<button id="chatbot-refresh" class="button"><?php esc_html_e( 'Refresh', 'chatbot-dashboard' ); ?></button>
	</div>

	<table class="wp-list-table widefat fixed striped">
		<thead>
			<tr>
				<th><?php esc_html_e( 'ID', 'chatbot-dashboard' ); ?></th>
				<th><?php esc_html_e( 'Session', 'chatbot-dashboard' ); ?></th>
				<th><?php esc_html_e( 'Query', 'chatbot-dashboard' ); ?></th>
				<th><?php esc_html_e( 'Intent', 'chatbot-dashboard' ); ?></th>
				<th><?php esc_html_e( 'Confidence', 'chatbot-dashboard' ); ?></th>
				<th><?php esc_html_e( 'Latency', 'chatbot-dashboard' ); ?></th>
				<th><?php esc_html_e( 'Status', 'chatbot-dashboard' ); ?></th>
				<th><?php esc_html_e( 'Date', 'chatbot-dashboard' ); ?></th>
				<th><?php esc_html_e( 'Actions', 'chatbot-dashboard' ); ?></th>
			</tr>
		</thead>
		<tbody id="chatbot-conv-table">
			<tr><td colspan="9"><?php esc_html_e( 'Loading…', 'chatbot-dashboard' ); ?></td></tr>
		</tbody>
	</table>

	<div id="chatbot-conv-pagination" class="chatbot-pagination"></div>
</div>
