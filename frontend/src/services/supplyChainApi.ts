import { API_BASE_URL } from "../context/apiConfig";
import { csrfHeaders } from "../csrf";

export interface ForecastRequest {
  history: number[];
  periods?: number;
}

export interface ForecastResponse {
  forecast?: number[];
  method?: string;
  history_points?: number;
  trend_per_period?: number;
  error?: string;
  detail?: string;
}

export interface RouteRequest {
  distance_matrix: number[][];
  num_vehicles?: number;
  depot?: number;
}

export interface RouteResponse {
  routes?: { stops: number[]; distance: number }[];
  total_distance?: number;
  method?: string;
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
  method?: string;
  components?: {
    lead_time_variability: number;
    defect_rate: number;
    on_time: number;
  };
  error?: string;
  detail?: string;
}

export interface AnomalyRequest {
  values: number[];
  threshold?: number;
}

export interface AnomalyResponse {
  anomalies?: { index: number; value: number; z?: number; score?: number }[];
  count?: number;
  threshold?: number;
  method?: string;
  error?: string;
  detail?: string;
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
  daily_demand?: number;
  service_level?: number;
  z_score?: number;
  method?: string;
  error?: string;
  detail?: string;
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
