<?php
/**
 * Activator — runs once on plugin activation.
 *
 * Creates two custom tables via dbDelta() and inserts seed data so the
 * dashboard is immediately usable for demos / learning.
 *
 * @package Chatbot_Dashboard
 */

namespace Chatbot_Dashboard;

defined( 'ABSPATH' ) || exit;

class Activator {

	/**
	 * Create tables and seed data.
	 */
	public static function activate(): void {
		self::create_tables();
		self::seed_data();
	}

	/**
	 * Create custom tables using dbDelta().
	 *
	 * dbDelta() compares the existing schema and only applies diffs,
	 * making it safe to run on every activation.
	 *
	 * @global \wpdb $wpdb
	 */
	private static function create_tables(): void {
		global $wpdb;

		$charset_collate = $wpdb->get_charset_collate();

		$sql_conversations = "CREATE TABLE {$wpdb->prefix}chatbot_conversations (
			id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
			session_id VARCHAR(64) NOT NULL,
			user_query TEXT NOT NULL,
			agent_response LONGTEXT,
			intent VARCHAR(32) DEFAULT 'rag',
			confidence_score DECIMAL(5,4) DEFAULT 0.0000,
			latency_ms INT UNSIGNED DEFAULT 0,
			status VARCHAR(16) DEFAULT 'success',
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			INDEX idx_session (session_id),
			INDEX idx_intent (intent),
			INDEX idx_status (status),
			INDEX idx_created (created_at)
		) {$charset_collate};";

		$sql_documents = "CREATE TABLE {$wpdb->prefix}chatbot_documents (
			id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
			file_name VARCHAR(255) NOT NULL,
			file_type VARCHAR(16) DEFAULT '',
			file_size BIGINT UNSIGNED DEFAULT 0,
			chunk_count INT UNSIGNED DEFAULT 0,
			embedding_status VARCHAR(16) DEFAULT 'pending',
			uploaded_by BIGINT UNSIGNED DEFAULT 0,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			INDEX idx_status (embedding_status),
			INDEX idx_created (created_at)
		) {$charset_collate};";

		require_once ABSPATH . 'wp-admin/includes/upgrade.php';
		dbDelta( $sql_conversations );
		dbDelta( $sql_documents );
	}

	/**
	 * Insert demo data so the dashboard is meaningful immediately.
	 */
	private static function seed_data(): void {
		global $wpdb;

		$conv_table = $wpdb->prefix . 'chatbot_conversations';
		$doc_table  = $wpdb->prefix . 'chatbot_documents';

		$existing = $wpdb->get_var( "SELECT COUNT(*) FROM {$conv_table}" ); // phpcs:ignore
		if ( $existing > 0 ) {
			return;
		}

		$intents = array( 'rag', 'report', 'compare', 'research', 'action' );
		$now     = current_time( 'mysql' );

		for ( $i = 1; $i <= 25; $i++ ) {
			$intent = $intents[ array_rand( $intents ) ];
			$wpdb->insert( // phpcs:ignore
				$conv_table,
				array(
					'session_id'      => 'demo-' . uniqid(),
					'user_query'      => "Demo query #{$i}: How do I use this system?",
					'agent_response'  => "This is a sample response for intent {$intent}.",
					'intent'          => $intent,
					'confidence_score' => wp_rand( 40, 99 ) / 100,
					'latency_ms'      => wp_rand( 200, 8000 ),
					'status'          => wp_rand( 0, 10 ) > 7 ? 'error' : 'success',
					'created_at'      => gmdate( 'Y-m-d H:i:s', strtotime( "-{$i} hours" ) ),
				)
			);
		}

		$doc_names = array(
			'annual-report-2025.pdf',
			'product-specs.docx',
			'meeting-notes.txt',
			'engineering-8d-report.pdf',
			'training-manual.docx',
		);

		foreach ( $doc_names as $name ) {
			$wpdb->insert( // phpcs:ignore
				$doc_table,
				array(
					'file_name'        => $name,
					'file_type'        => pathinfo( $name, PATHINFO_EXTENSION ),
					'file_size'        => wp_rand( 10000, 5000000 ),
					'chunk_count'      => wp_rand( 5, 120 ),
					'embedding_status' => array_rand( array_flip( array( 'done', 'done', 'done', 'pending', 'failed' ) ) ),
					'uploaded_by'      => 1,
					'created_at'       => gmdate( 'Y-m-d H:i:s', strtotime( '-' . wp_rand( 1, 30 ) . ' days' ) ),
				)
			);
		}
	}
}
