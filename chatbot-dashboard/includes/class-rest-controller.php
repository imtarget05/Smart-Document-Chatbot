<?php
/**
 * Rest_Controller — registers custom REST API routes under chatbot-dashboard/v1.
 *
 * Each route includes a permission_callback that checks current_user_can('manage_options').
 * Write-operations also verify the WordPress REST API nonce sent via X-WP-Nonce header.
 *
 * @package Chatbot_Dashboard
 */

namespace Chatbot_Dashboard;

defined( 'ABSPATH' ) || exit;

class Rest_Controller {

	/**
	 * @var Database
	 */
	private $db;

	public function __construct() {
		$this->db = new Database();
	}

	/**
	 * Hook into rest_api_init.
	 */
	public function init(): void {
		add_action( 'rest_api_init', array( $this, 'register_routes' ) );
	}

	/**
	 * Register all routes under chatbot-dashboard/v1.
	 */
	public function register_routes(): void {
		// GET /conversations — paginated list with optional filters.
		register_rest_route(
			'chatbot-dashboard/v1',
			'/conversations',
			array(
				'methods'             => 'GET',
				'callback'            => array( $this, 'get_conversations' ),
				'permission_callback' => array( $this, 'check_permission' ),
				'args'                => array(
					'page'   => array(
						'default'           => 1,
						'sanitize_callback' => 'absint',
					),
					'per'    => array(
						'default'           => 20,
						'sanitize_callback' => 'absint',
					),
					'intent' => array(
						'default'           => '',
						'sanitize_callback' => 'sanitize_text_field',
					),
					'status' => array(
						'default'           => '',
						'sanitize_callback' => 'sanitize_text_field',
					),
				),
			)
		);

		// DELETE /conversations/{id} — delete a single log entry.
		register_rest_route(
			'chatbot-dashboard/v1',
			'/conversations/(?P<id>\d+)',
			array(
				'methods'             => 'DELETE',
				'callback'            => array( $this, 'delete_conversation' ),
				'permission_callback' => array( $this, 'check_permission' ),
				'args'                => array(
					'id' => array(
						'required'          => true,
						'sanitize_callback' => 'absint',
					),
				),
			)
		);

		// GET /stats — aggregate stats for the overview page.
		register_rest_route(
			'chatbot-dashboard/v1',
			'/stats',
			array(
				'methods'             => 'GET',
				'callback'            => array( $this, 'get_stats' ),
				'permission_callback' => array( $this, 'check_permission' ),
			)
		);

		// GET /documents — paginated document list.
		register_rest_route(
			'chatbot-dashboard/v1',
			'/documents',
			array(
				'methods'             => 'GET',
				'callback'            => array( $this, 'get_documents' ),
				'permission_callback' => array( $this, 'check_permission' ),
				'args'                => array(
					'page' => array(
						'default'           => 1,
						'sanitize_callback' => 'absint',
					),
					'per'  => array(
						'default'           => 20,
						'sanitize_callback' => 'absint',
					),
				),
			)
		);

		// GET /ab-variants — current A/B variant statuses.
		register_rest_route(
			'chatbot-dashboard/v1',
			'/ab-variants',
			array(
				'methods'             => 'GET',
				'callback'            => array( $this, 'get_ab_variants' ),
				'permission_callback' => array( $this, 'check_permission' ),
			)
		);

		// PUT /ab-variants — toggle a variant on/off.
		register_rest_route(
			'chatbot-dashboard/v1',
			'/ab-variants',
			array(
				'methods'             => 'PUT',
				'callback'            => array( $this, 'update_ab_variant' ),
				'permission_callback' => array( $this, 'check_permission' ),
				'args'                => array(
					'variant_id' => array(
						'required'          => true,
						'sanitize_callback' => 'sanitize_text_field',
					),
					'active'     => array(
						'required'          => true,
						'sanitize_callback' => 'rest_sanitize_boolean',
					),
				),
			)
		);
	}

	/**
	 * Permission check — only admins.
	 *
	 * @return bool|\WP_Error
	 */
	public function check_permission() {
		if ( ! current_user_can( 'manage_options' ) ) {
			return new \WP_Error(
				'rest_forbidden',
				__( 'You do not have permission to access this resource.', 'chatbot-dashboard' ),
				array( 'status' => 403 )
			);
		}
		return true;
	}

	// ── Callbacks ────────────────────────────────────────────────────────

	public function get_conversations( \WP_REST_Request $request ): \WP_REST_Response {
		$page   = (int) $request->get_param( 'page' );
		$per    = (int) $request->get_param( 'per' );
		$intent = $request->get_param( 'intent' );
		$status = $request->get_param( 'status' );

		$data = $this->db->get_conversations( $page, $per, $intent, $status );
		return new \WP_REST_Response( $data, 200 );
	}

	public function delete_conversation( \WP_REST_Request $request ): \WP_REST_Response {
		$id = (int) $request->get_param( 'id' );
		$deleted = $this->db->delete_conversation( $id );

		if ( ! $deleted ) {
			return new \WP_REST_Response(
				array( 'message' => __( 'Conversation not found.', 'chatbot-dashboard' ) ),
				404
			);
		}

		return new \WP_REST_Response(
			array( 'message' => __( 'Conversation deleted.', 'chatbot-dashboard' ) ),
			200
		);
	}

	public function get_stats( \WP_REST_Request $request ): \WP_REST_Response { // phpcs:ignore
		return new \WP_REST_Response( $this->db->get_stats(), 200 );
	}

	public function get_documents( \WP_REST_Request $request ): \WP_REST_Response {
		$page = (int) $request->get_param( 'page' );
		$per  = (int) $request->get_param( 'per' );

		return new \WP_REST_Response( $this->db->get_documents( $page, $per ), 200 );
	}

	public function get_ab_variants( \WP_REST_Request $request ): \WP_REST_Response { // phpcs:ignore
		return new \WP_REST_Response( $this->db->get_ab_variants(), 200 );
	}

	public function update_ab_variant( \WP_REST_Request $request ): \WP_REST_Response {
		$variant_id = $request->get_param( 'variant_id' );
		$active     = (bool) $request->get_param( 'active' );

		$this->db->set_ab_variant_status( $variant_id, $active );

		return new \WP_REST_Response(
			array(
				'message'    => __( 'Variant updated.', 'chatbot-dashboard' ),
				'variants'   => $this->db->get_ab_variants(),
			),
			200
		);
	}
}
