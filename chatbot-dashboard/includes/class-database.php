<?php
/**
 * Database — $wpdb wrapper for all custom table queries.
 *
 * Centralises every SQL statement so the rest of the plugin never
 * touches $wpdb directly. This makes future schema changes and
 * unit-testing much easier.
 *
 * @package Chatbot_Dashboard
 */

namespace Chatbot_Dashboard;

defined( 'ABSPATH' ) || exit;

class Database {

	/**
	 * @var \wpdb
	 */
	private $wpdb;

	/**
	 * @var string
	 */
	private $conv_table;

	/**
	 * @var string
	 */
	private $doc_table;

	public function __construct() {
		global $wpdb;
		$this->wpdb       = $wpdb;
		$this->conv_table = $wpdb->prefix . 'chatbot_conversations';
		$this->doc_table  = $wpdb->prefix . 'chatbot_documents';
	}

	// ── Conversations ────────────────────────────────────────────────────

	/**
	 * Return paginated conversations with optional intent/status filter.
	 *
	 * @param int    $page   Current page (1-based).
	 * @param int    $per    Items per page.
	 * @param string $intent Optional intent filter.
	 * @param string $status Optional status filter.
	 * @return array{ items: array[], total: int }
	 */
	public function get_conversations( int $page = 1, int $per = 20, string $intent = '', string $status = '' ): array {
		$where = array( '1=1' );
		if ( ! empty( $intent ) ) {
			$where[] = $this->wpdb->prepare( 'intent = %s', $intent );
		}
		if ( ! empty( $status ) ) {
			$where[] = $this->wpdb->prepare( 'status = %s', $status );
		}
		$where_sql = implode( ' AND ', $where );

		$total = (int) $this->wpdb->get_var(
			"SELECT COUNT(*) FROM {$this->conv_table} WHERE {$where_sql}" // phpcs:ignore
		);

		$offset = max( 0, ( $page - 1 ) * $per );
		$items  = $this->wpdb->get_results( // phpcs:ignore
			$this->wpdb->prepare(
				"SELECT * FROM {$this->conv_table} WHERE {$where_sql} ORDER BY created_at DESC LIMIT %d OFFSET %d", // phpcs:ignore
				$per,
				$offset
			),
			ARRAY_A
		);

		return array(
			'items' => $items ?: array(),
			'total' => $total,
		);
	}

	/**
	 * Aggregate stats for the dashboard overview.
	 *
	 * @return array
	 */
	public function get_stats(): array {
		$today = gmdate( 'Y-m-d' );

		$total_today = (int) $this->wpdb->get_var(
			$this->wpdb->prepare(
				"SELECT COUNT(*) FROM {$this->conv_table} WHERE DATE(created_at) = %s", // phpcs:ignore
				$today
			)
		);

		$avg_latency = (float) $this->wpdb->get_var(
			"SELECT AVG(latency_ms) FROM {$this->conv_table} WHERE status = 'success'" // phpcs:ignore
		);

		$intent_breakdown = $this->wpdb->get_results( // phpcs:ignore
			"SELECT intent, COUNT(*) as count FROM {$this->conv_table} GROUP BY intent ORDER BY count DESC",
			ARRAY_A
		);

		$error_rate = $this->wpdb->get_var( // phpcs:ignore
			"SELECT ( COUNT(CASE WHEN status = 'error' THEN 1 END) / COUNT(*) ) * 100 FROM {$this->conv_table}"
		);

		return array(
			'total_today'      => $total_today,
			'avg_latency_ms'   => round( $avg_latency, 0 ),
			'intent_breakdown' => $intent_breakdown ?: array(),
			'error_rate'       => round( (float) $error_rate, 1 ),
		);
	}

	/**
	 * Return a single conversation by ID.
	 *
	 * @param int $id
	 * @return array|null
	 */
	public function get_conversation( int $id ): ?array {
		$row = $this->wpdb->get_row( // phpcs:ignore
			$this->wpdb->prepare( "SELECT * FROM {$this->conv_table} WHERE id = %d", $id ),
			ARRAY_A
		);
		return $row ?: null;
	}

	// ── Documents ────────────────────────────────────────────────────────

	/**
	 * Return paginated documents.
	 *
	 * @param int $page
	 * @param int $per
	 * @return array{ items: array[], total: int }
	 */
	public function get_documents( int $page = 1, int $per = 20 ): array {
		$total = (int) $this->wpdb->get_var(
			"SELECT COUNT(*) FROM {$this->doc_table}" // phpcs:ignore
		);

		$offset = max( 0, ( $page - 1 ) * $per );
		$items  = $this->wpdb->get_results( // phpcs:ignore
			$this->wpdb->prepare(
				"SELECT * FROM {$this->doc_table} ORDER BY created_at DESC LIMIT %d OFFSET %d",
				$per,
				$offset
			),
			ARRAY_A
		);

		return array(
			'items' => $items ?: array(),
			'total' => $total,
		);
	}

	/**
	 * Delete a conversation log entry.
	 *
	 * @param int $id
	 * @return bool
	 */
	public function delete_conversation( int $id ): bool {
		return (bool) $this->wpdb->delete(
			$this->conv_table,
			array( 'id' => $id ),
			array( '%d' )
		);
	}

	/**
	 * Update A/B testing variant status (active / inactive).
	 *
	 * Stores as a simple option since config is small and key-value.
	 *
	 * @param string $variant_id
	 * @param bool   $active
	 */
	public function set_ab_variant_status( string $variant_id, bool $active ): void {
		$variants = get_option( 'chatbot_ab_variants', array() );
		$variants[ $variant_id ] = $active;
		update_option( 'chatbot_ab_variants', $variants );
	}

	/**
	 * Get all A/B testing variants with their statuses.
	 *
	 * @return array
	 */
	public function get_ab_variants(): array {
		$defaults = array(
			'control'   => true,
			'variant-a' => true,
			'variant-b' => false,
			'variant-c' => false,
		);
		$saved    = get_option( 'chatbot_ab_variants', array() );
		return wp_parse_args( $saved, $defaults );
	}
}
