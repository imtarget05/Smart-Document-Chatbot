<?php
/**
 * Overview — aggregate stats rendered on page load via REST fetch.
 *
 * The JS in dashboard.js fetches GET /stats and populates the summary cards
 * and the intent-breakdown chart automatically.
 *
 * @package Chatbot_Dashboard
 */

defined( 'ABSPATH' ) || exit;

if ( ! current_user_can( 'manage_options' ) ) {
	wp_die( esc_html__( 'You do not have sufficient permissions.', 'chatbot-dashboard' ) );
}
?>
<div class="wrap chatbot-dashboard-wrap">
	<h1><?php echo esc_html__( 'Chatbot Dashboard — Overview', 'chatbot-dashboard' ); ?></h1>

	<div id="chatbot-stats-cards" class="chatbot-cards">
		<div class="chatbot-card">
			<span class="chatbot-card-label"><?php esc_html_e( 'Queries Today', 'chatbot-dashboard' ); ?></span>
			<span class="chatbot-card-value" data-stat="total_today">—</span>
		</div>
		<div class="chatbot-card">
			<span class="chatbot-card-label"><?php esc_html_e( 'Avg Latency', 'chatbot-dashboard' ); ?></span>
			<span class="chatbot-card-value" data-stat="avg_latency_ms">—</span>
			<span class="chatbot-card-unit">ms</span>
		</div>
		<div class="chatbot-card">
			<span class="chatbot-card-label"><?php esc_html_e( 'Error Rate', 'chatbot-dashboard' ); ?></span>
			<span class="chatbot-card-value" data-stat="error_rate">—</span>
			<span class="chatbot-card-unit">%</span>
		</div>
	</div>

	<div class="chatbot-chart-row">
		<div class="chatbot-chart-box">
			<h2><?php esc_html_e( 'Intent Breakdown', 'chatbot-dashboard' ); ?></h2>
			<canvas id="chatbot-intent-chart" width="300" height="200"></canvas>
		</div>
		<div class="chatbot-chart-box">
			<h2><?php esc_html_e( 'Recent Activity', 'chatbot-dashboard' ); ?></h2>
			<table class="wp-list-table widefat fixed striped">
				<thead>
					<tr>
						<th><?php esc_html_e( 'Query', 'chatbot-dashboard' ); ?></th>
						<th><?php esc_html_e( 'Intent', 'chatbot-dashboard' ); ?></th>
						<th><?php esc_html_e( 'Latency', 'chatbot-dashboard' ); ?></th>
						<th><?php esc_html_e( 'Status', 'chatbot-dashboard' ); ?></th>
					</tr>
				</thead>
				<tbody id="chatbot-recent-table">
					<tr><td colspan="4"><?php esc_html_e( 'Loading…', 'chatbot-dashboard' ); ?></td></tr>
				</tbody>
			</table>
		</div>
	</div>
</div>
