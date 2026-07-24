import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../context/AuthContext";

const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string) || "http://localhost:8080/api";

interface ConceptNode {
  id: string;
  label: string;
  type: string;
  description: string;
  x?: number;
  y?: number;
}

interface ConceptEdge {
  source: string;
  target: string;
}

interface MindMapData {
  nodes: ConceptNode[];
  edges: ConceptEdge[];
}

interface ConceptMapProps {
  documentId: number;
  documentName: string;
  onAskAI: (concept: string) => void;
}

function ConceptMap({ documentId, documentName, onAskAI }: ConceptMapProps) {
  const [selectedNode, setSelectedNode] = useState<ConceptNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<ConceptNode | null>(null);
  const { token } = useAuth();

  // SVG Canvas configuration
  const width = 800;
  const height = 550;
  const centerX = width / 2;
  const centerY = height / 2;

  // React Query fetch for Mind Map data
  const {
    data,
    isLoading,
    error,
    refetch: fetchMindMap,
  } = useQuery<MindMapData>({
    queryKey: ["mindmap", documentId],
    queryFn: async () => {
      setSelectedNode(null);
      const response = await fetch(
        `${API_BASE_URL}/documents/${documentId}/mindmap`,
        {
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        },
      );
      if (!response.ok) {
        throw new Error("Failed to load mind map data");
      }
      return response.json();
    },
  });

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 bg-gray-50/50">
        <div className="relative w-16 h-16 mb-4">
          <div className="absolute inset-0 rounded-full border-4 border-indigo-200 animate-pulse"></div>
          <div className="absolute inset-0 rounded-full border-4 border-t-indigo-600 animate-spin"></div>
        </div>
        <p className="text-sm font-semibold text-gray-700">
          AI is mapping document concepts...
        </p>
        <p className="text-xs text-gray-400 mt-1">
          This takes just a moment for deep analytical modeling.
        </p>
      </div>
    );
  }

  if (error || !data || !data.nodes || data.nodes.length === 0) {
    const errorMsg =
      error instanceof Error ? error.message : "No concepts found.";
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 bg-gray-50/50">
        <div className="text-4xl mb-3">⚠️</div>
        <p className="text-sm font-semibold text-gray-700">
          Could not generate concept map
        </p>
        <p className="text-xs text-gray-400 mt-1 mb-4">{errorMsg}</p>
        <button
          onClick={() => fetchMindMap()}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
        >
          Try Again
        </button>
      </div>
    );
  }

  // Calculate coordinates for concept nodes in a radial layout
  const nodes = data.nodes;
  const edges = data.edges || [];
  const radius = 180; // Distance of satellite nodes from center

  const nodesWithCoords = nodes.map((node, i) => {
    const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
    const x = centerX + radius * Math.cos(angle);
    const y = centerY + radius * Math.sin(angle);
    return { ...node, x, y };
  });

  const centerNode: ConceptNode & { x: number; y: number } = {
    id: "center",
    label: documentName,
    type: "Document",
    description: "Target document under conceptual analysis.",
    x: centerX,
    y: centerY,
  };

  const allNodes = [centerNode, ...nodesWithCoords];

  const getNodeColor = (type?: string) => {
    switch (type?.toLowerCase()) {
      case "document":
        return "from-slate-700 to-slate-900 border-slate-600 shadow-slate-200 text-white";
      case "core":
        return "from-indigo-500 to-indigo-600 border-indigo-400 shadow-indigo-100 text-white";
      case "financial":
        return "from-emerald-500 to-emerald-600 border-emerald-400 shadow-emerald-100 text-white";
      case "technical":
        return "from-sky-500 to-sky-600 border-sky-400 shadow-sky-100 text-white";
      case "process":
        return "from-amber-500 to-amber-600 border-amber-400 shadow-amber-100 text-white";
      case "metric":
        return "from-rose-500 to-rose-600 border-rose-400 shadow-rose-100 text-white";
      default:
        return "from-violet-500 to-violet-600 border-violet-400 shadow-violet-100 text-white";
    }
  };

  const getCategoryBadgeColor = (type?: string) => {
    switch (type?.toLowerCase()) {
      case "core":
        return "bg-indigo-100 text-indigo-800";
      case "financial":
        return "bg-emerald-100 text-emerald-800";
      case "technical":
        return "bg-sky-100 text-sky-800";
      case "process":
        return "bg-amber-100 text-amber-800";
      case "metric":
        return "bg-rose-100 text-rose-800";
      default:
        return "bg-violet-100 text-violet-800";
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden bg-gray-50/30 relative">
      {/* Mind Map Canvas */}
      <div className="flex-1 relative flex items-center justify-center p-4">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-full max-w-4xl border border-gray-200/50 rounded-2xl bg-white shadow-sm shadow-gray-100/50 select-none overflow-visible"
        >
          {/* Defs for glowing edges */}
          <defs>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <linearGradient id="edgeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#818cf8" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.4" />
            </linearGradient>
          </defs>

          {/* Draw connection curves from center to concept nodes */}
          {nodesWithCoords.map((node) => {
            const dx = node.x - centerX;
            const dy = node.y - centerY;
            const cx1 = centerX + dx * 0.25;
            const cy1 = centerY + dy * 0.75;
            const cx2 = centerX + dx * 0.75;
            const cy2 = centerY + dy * 0.25;
            const pathStr = `M ${centerX} ${centerY} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${node.x} ${node.y}`;

            const isHighlighted =
              hoveredNode?.id === node.id || selectedNode?.id === node.id;

            return (
              <g key={`edge-${node.id}`}>
                <path
                  d={pathStr}
                  fill="none"
                  stroke={isHighlighted ? "#6366f1" : "url(#edgeGrad)"}
                  strokeWidth={isHighlighted ? 3 : 1.5}
                  strokeDasharray={isHighlighted ? "0" : "4,4"}
                  className="transition-all duration-300"
                />
                {isHighlighted && (
                  <path
                    d={pathStr}
                    fill="none"
                    stroke="#818cf8"
                    strokeWidth={6}
                    strokeOpacity={0.2}
                    filter="url(#glow)"
                  />
                )}
              </g>
            );
          })}

          {/* Draw concept relationships (cross links) */}
          {edges.map((edge, idx) => {
            const sourceNode = allNodes.find((n) => n.id === edge.source);
            const targetNode = allNodes.find((n) => n.id === edge.target);

            if (
              !sourceNode ||
              !targetNode ||
              sourceNode.x === undefined ||
              sourceNode.y === undefined ||
              targetNode.x === undefined ||
              targetNode.y === undefined
            )
              return null;

            const dx = targetNode.x - sourceNode.x;
            const dy = targetNode.y - sourceNode.y;
            const cx = sourceNode.x + dx * 0.5 - dy * 0.15; // Offset to create curves
            const cy = sourceNode.y + dy * 0.5 + dx * 0.15;
            const pathStr = `M ${sourceNode.x} ${sourceNode.y} Q ${cx} ${cy} ${targetNode.x} ${targetNode.y}`;

            const isEdgeHighlighted =
              hoveredNode?.id === edge.source ||
              hoveredNode?.id === edge.target ||
              selectedNode?.id === edge.source ||
              selectedNode?.id === edge.target;

            return (
              <g key={`cross-edge-${idx}`}>
                <path
                  d={pathStr}
                  fill="none"
                  stroke={isEdgeHighlighted ? "#4f46e5" : "#e2e8f0"}
                  strokeWidth={isEdgeHighlighted ? 1.5 : 1}
                  strokeOpacity={isEdgeHighlighted ? 0.8 : 0.5}
                  className="transition-all duration-300"
                />
              </g>
            );
          })}

          {/* Render Concept Nodes */}
          {allNodes.map((node) => {
            if (node.x === undefined || node.y === undefined) return null;
            const isCenter = node.id === "center";
            const size = isCenter ? 48 : 28;
            const isHovered = hoveredNode?.id === node.id;
            const isSelected = selectedNode?.id === node.id;

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                onMouseEnter={() => !isCenter && setHoveredNode(node)}
                onMouseLeave={() => setHoveredNode(null)}
                onClick={() => !isCenter && setSelectedNode(node)}
                className={`cursor-pointer transition-all duration-300 ${
                  isCenter ? "" : "hover:scale-110"
                }`}
              >
                {/* Outer Glow */}
                {(isHovered || isSelected) && (
                  <circle
                    r={size + 6}
                    fill="none"
                    stroke="#a5b4fc"
                    strokeWidth="2"
                    strokeOpacity="0.8"
                    filter="url(#glow)"
                  />
                )}

                {/* Node Circle */}
                <circle
                  r={size}
                  className={`transition-all duration-300 shadow-md ${
                    isCenter
                      ? "fill-slate-800 stroke-slate-700"
                      : isSelected
                        ? "fill-indigo-600 stroke-indigo-500"
                        : "fill-white stroke-indigo-200"
                  }`}
                  strokeWidth={isSelected || isCenter ? 2 : 1.5}
                />

                {/* Styled Center Gradients inside circle */}
                <foreignObject
                  x={-size + 2}
                  y={-size + 2}
                  width={(size - 2) * 2}
                  height={(size - 2) * 2}
                  className="rounded-full overflow-hidden pointer-events-none"
                >
                  <div
                    className={`w-full h-full rounded-full flex flex-col items-center justify-center p-1.5 bg-gradient-to-tr text-center ${getNodeColor(
                      isCenter ? "document" : node.type,
                    )}`}
                  >
                    {!isCenter && (
                      <span className="text-[10px] uppercase font-bold tracking-wider scale-90 opacity-80 leading-none">
                        {node.type}
                      </span>
                    )}
                    <span
                      className={`font-semibold truncate max-w-full leading-snug mt-0.5 ${
                        isCenter ? "text-xs" : "text-[10px]"
                      }`}
                    >
                      {isCenter ? "DOCUMENT" : node.label}
                    </span>
                  </div>
                </foreignObject>
              </g>
            );
          })}
        </svg>

        {/* Legend overlays */}
        <div className="absolute bottom-6 left-6 bg-white/80 backdrop-blur-md px-3 py-2 rounded-xl border border-gray-200/50 shadow-sm flex flex-wrap gap-x-3 gap-y-1 max-w-md">
          <div className="flex items-center gap-1.5 text-[10px] font-bold text-gray-500">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-800"></span>{" "}
            Document
          </div>
          <div className="flex items-center gap-1.5 text-[10px] font-bold text-gray-500">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500"></span>{" "}
            Core
          </div>
          <div className="flex items-center gap-1.5 text-[10px] font-bold text-gray-500">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>{" "}
            Financial
          </div>
          <div className="flex items-center gap-1.5 text-[10px] font-bold text-gray-500">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-500"></span>{" "}
            Technical
          </div>
          <div className="flex items-center gap-1.5 text-[10px] font-bold text-gray-500">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>{" "}
            Process
          </div>
          <div className="flex items-center gap-1.5 text-[10px] font-bold text-gray-500">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>{" "}
            Metric
          </div>
        </div>
      </div>

      {/* Selected Concept Detail Drawer */}
      <div
        className={`w-72 border-l border-gray-200 bg-white shadow-2xl flex flex-col transition-all duration-300 absolute md:relative right-0 top-0 bottom-0 z-20 ${
          selectedNode
            ? "translate-x-0"
            : "translate-x-full md:w-0 overflow-hidden border-l-0"
        }`}
      >
        {selectedNode && (
          <div className="p-5 flex-1 flex flex-col justify-between overflow-y-auto">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${getCategoryBadgeColor(selectedNode.type)}`}
                >
                  {selectedNode.type}
                </span>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-gray-400 hover:text-gray-600 transition text-lg"
                >
                  &times;
                </button>
              </div>

              <div>
                <h4 className="text-base font-bold text-gray-800 mb-1">
                  {selectedNode.label}
                </h4>
                <div className="h-0.5 w-10 bg-indigo-500 rounded"></div>
              </div>

              <div className="bg-gray-50 p-3.5 rounded-xl border border-gray-100">
                <h5 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">
                  Concept definition
                </h5>
                <p className="text-xs text-gray-600 leading-relaxed font-medium">
                  {selectedNode.description ||
                    "No definition available for this concept."}
                </p>
              </div>
            </div>

            <button
              onClick={() => onAskAI(selectedNode.label)}
              className="mt-6 w-full py-2.5 px-4 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white text-xs font-bold rounded-xl shadow-md shadow-indigo-100 hover:shadow-indigo-200 transition-all duration-300 flex items-center justify-center gap-1.5"
            >
              <span>💬</span> Ask AI about this Concept
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default ConceptMap;
