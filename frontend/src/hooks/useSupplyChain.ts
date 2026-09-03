import { useMutation } from "@tanstack/react-query";
import {
  supplyChainApi,
  type ForecastRequest,
  type ForecastResponse,
  type RouteRequest,
  type RouteResponse,
  type SupplierRiskRequest,
  type SupplierRiskResponse,
  type AnomalyRequest,
  type AnomalyResponse,
  type InventoryRequest,
  type InventoryResponse,
} from "../services/supplyChainApi";

export function useForecast() {
  return useMutation<ForecastResponse, Error, ForecastRequest>({
    mutationFn: (body) => supplyChainApi.forecast(body),
  });
}

export function useOptimizeRoute() {
  return useMutation<RouteResponse, Error, RouteRequest>({
    mutationFn: (body) => supplyChainApi.optimizeRoute(body),
  });
}

export function useSupplierRisk() {
  return useMutation<SupplierRiskResponse, Error, SupplierRiskRequest>({
    mutationFn: (body) => supplyChainApi.supplierRisk(body),
  });
}

export function useAnomalyDetect() {
  return useMutation<AnomalyResponse, Error, AnomalyRequest>({
    mutationFn: (body) => supplyChainApi.anomalyDetect(body),
  });
}

export function useInventoryOptimalOrder() {
  return useMutation<InventoryResponse, Error, InventoryRequest>({
    mutationFn: (body) => supplyChainApi.inventoryOptimalOrder(body),
  });
}