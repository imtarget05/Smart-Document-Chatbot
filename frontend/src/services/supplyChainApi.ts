import { API_BASE_URL } from "../context/apiConfig";
import { csrfHeaders } from "../csrf";

export interface ForecastRequest {
  history: number[];
  periods?: number;
}

export interface ForecastResponse {
  forecast?: number[];
  error?: string;
}

export interface RouteRequest {
  distance_matrix: number[][];
  num_vehicles?: number;
  depot?: number;
}

export interface RouteResponse {
  routes?: unknown[];
  total_distance?: number;
  error?: string;
}

export interface SupplierRiskRequest {
  lead_time_std: number;
  defect_rate: number;
  on_time_rate: number;
}

export interface SupplierRiskResponse {
  risk_score?: number;
  risk_grade?: string;
  error?: string;
}

export interface AnomalyRequest {
  values: number[];
  threshold?: number;
}

export interface AnomalyResponse {
  anomalies?: number[];
  indices?: number[];
  error?: string;
}

export interface InventoryRequest {
  annual_demand: number;
  order_cost: number;
  holding_cost: number;
  std_demand?: number;
  lead_time_days?: number;
  service_level?: number;
}

export interface InventoryResponse {
  eoq?: number;
  safety_stock?: number;
  reorder_point?: number;
  error?: string;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}/supply-chain${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await csrfHeaders()) },
    credentials: "include",
    body: JSON.stringify(body),
  });
  return res.json();
}

export const supplyChainApi = {
  forecast: (body: ForecastRequest) => post<ForecastResponse>("/forecast", body),
  optimizeRoute: (body: RouteRequest) => post<RouteResponse>("/optimize-route", body),
  supplierRisk: (body: SupplierRiskRequest) => post<SupplierRiskResponse>("/supplier-risk", body),
  anomalyDetect: (body: AnomalyRequest) => post<AnomalyResponse>("/anomaly-detect", body),
  inventoryOptimalOrder: (body: InventoryRequest) => post<InventoryResponse>("/inventory-optimal-order", body),
};
