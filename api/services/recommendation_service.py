"""Smart spot instance recommendation service.

This service analyzes spot SKUs and provides intelligent recommendations
based on multiple factors including price, eviction rates, performance,
and availability.
"""

from typing import List, Dict, Any, Optional, Literal
from dataclasses import dataclass


@dataclass
class RecommendationCriteria:
    """Criteria for spot instance recommendations."""

    # Primary constraints
    max_hourly_cost: Optional[float] = None  # Maximum acceptable hourly cost
    max_eviction_rate: Optional[
        str
    ] = None  # Maximum eviction rate ("0-5", "5-10", etc.)
    min_availability_zones: int = 1  # Minimum availability zones required

    # Optimization preferences
    optimize_for: Literal["cost", "reliability", "performance", "balanced"] = "balanced"
    architecture_preference: Optional[
        str
    ] = None  # "x64", "Arm64", or None for no preference

    # Scoring weights (sum should equal 1.0)
    price_weight: float = 0.35
    eviction_weight: float = 0.25
    performance_weight: float = 0.20
    availability_weight: float = 0.10
    architecture_weight: float = 0.10


class RecommendationService:
    """Service for generating intelligent spot instance recommendations."""

    @staticmethod
    def recommend_top_skus(
        skus: List[Dict[str, Any]], criteria: RecommendationCriteria, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Recommend top spot SKUs based on multi-factor scoring.

        Args:
            skus: List of SKU data with pricing and eviction info
            criteria: Recommendation criteria and preferences
            limit: Maximum number of recommendations to return

        Returns:
            List of top-scored SKUs with recommendation scores and reasoning
        """
        if not skus:
            return []

        # Filter SKUs by hard constraints
        filtered_skus = RecommendationService._apply_constraints(skus, criteria)

        if not filtered_skus:
            return []

        # Score each SKU
        scored_skus = []
        for sku in filtered_skus:
            score = RecommendationService._calculate_sku_score(
                sku, filtered_skus, criteria
            )
            scored_sku = {
                **sku,
                "recommendation_score": score["total_score"],
                "score_breakdown": score["breakdown"],
                "recommendation_reason": score["reason"],
            }
            scored_skus.append(scored_sku)

        # Sort by score (highest first) and return top results
        scored_skus.sort(key=lambda x: x["recommendation_score"], reverse=True)

        return scored_skus[:limit]

    @staticmethod
    def _apply_constraints(
        skus: List[Dict[str, Any]], criteria: RecommendationCriteria
    ) -> List[Dict[str, Any]]:
        """Apply hard constraints to filter SKUs."""
        filtered = []

        for sku in skus:
            # Skip if missing required data
            if not sku.get("zones"):
                continue

            # Availability zones constraint
            if len(sku["zones"]) < criteria.min_availability_zones:
                continue

            # Cost constraint
            if criteria.max_hourly_cost is not None:
                price = sku.get("price")
                if price is not None and price > criteria.max_hourly_cost:
                    continue

            # Eviction rate constraint
            if criteria.max_eviction_rate is not None:
                eviction_rate = sku.get("eviction_rate")
                if eviction_rate is not None:
                    if not RecommendationService._is_eviction_rate_acceptable(
                        eviction_rate, criteria.max_eviction_rate
                    ):
                        continue

            filtered.append(sku)

        return filtered

    @staticmethod
    def _is_eviction_rate_acceptable(actual_rate: str, max_rate: str) -> bool:
        """Check if eviction rate meets constraint."""
        # Convert eviction rate ranges to numbers for comparison
        def rate_to_number(rate: str) -> float:
            if rate == "0-5":
                return 2.5
            elif rate == "5-10":
                return 7.5
            elif rate == "10-15":
                return 12.5
            elif rate == "15-20":
                return 17.5
            elif rate == "20+":
                return 25.0
            else:
                return 50.0  # Unknown = high risk

        return rate_to_number(actual_rate) <= rate_to_number(max_rate)

    @staticmethod
    def _calculate_sku_score(
        sku: Dict[str, Any],
        all_skus: List[Dict[str, Any]],
        criteria: RecommendationCriteria,
    ) -> Dict[str, Any]:
        """Calculate composite score for a SKU."""
        breakdown = {}
        reasoning_parts = []

        # 1. Price Score (lower price = higher score)
        price_score = RecommendationService._calculate_price_score(sku, all_skus)
        breakdown["price_score"] = price_score
        if price_score > 0.7:
            reasoning_parts.append("excellent pricing")
        elif price_score > 0.5:
            reasoning_parts.append("good pricing")

        # 2. Eviction Score (lower eviction rate = higher score)
        eviction_score = RecommendationService._calculate_eviction_score(sku)
        breakdown["eviction_score"] = eviction_score
        if eviction_score > 0.8:
            reasoning_parts.append("very low eviction risk")
        elif eviction_score > 0.6:
            reasoning_parts.append("low eviction risk")

        # 3. Performance Score (price/performance ratio)
        performance_score = RecommendationService._calculate_performance_score(
            sku, all_skus
        )
        breakdown["performance_score"] = performance_score
        if performance_score > 0.7:
            reasoning_parts.append("excellent value")

        # 4. Availability Score (more zones = higher score)
        availability_score = RecommendationService._calculate_availability_score(
            sku, all_skus
        )
        breakdown["availability_score"] = availability_score
        if availability_score > 0.8:
            reasoning_parts.append("high availability")

        # 5. Architecture Score
        architecture_score = RecommendationService._calculate_architecture_score(
            sku, criteria
        )
        breakdown["architecture_score"] = architecture_score
        if architecture_score > 0.8 and sku.get("architecture") == "Arm64":
            reasoning_parts.append("ARM64 efficiency advantage")

        # Calculate weighted total
        total_score = (
            price_score * criteria.price_weight
            + eviction_score * criteria.eviction_weight
            + performance_score * criteria.performance_weight
            + availability_score * criteria.availability_weight
            + architecture_score * criteria.architecture_weight
        )

        # Apply optimization preference adjustments
        if criteria.optimize_for == "cost":
            total_score = total_score * 0.7 + price_score * 0.3
            reasoning_parts.append("cost-optimized")
        elif criteria.optimize_for == "reliability":
            total_score = total_score * 0.7 + eviction_score * 0.3
            reasoning_parts.append("reliability-focused")
        elif criteria.optimize_for == "performance":
            total_score = total_score * 0.7 + performance_score * 0.3
            reasoning_parts.append("performance-optimized")

        reason = f"Recommended for {', '.join(reasoning_parts[:3])}"

        return {
            "total_score": round(total_score, 3),
            "breakdown": breakdown,
            "reason": reason,
        }

    @staticmethod
    def _calculate_price_score(
        sku: Dict[str, Any], all_skus: List[Dict[str, Any]]
    ) -> float:
        """Calculate price score (0-1, higher is better)."""
        price = sku.get("price")
        if price is None:
            return 0.5  # Neutral if no pricing data

        # Get prices for comparison (filter out None values)
        prices = [s.get("price") for s in all_skus if s.get("price") is not None]
        if not prices:
            return 0.5

        min_price = min(prices)
        max_price = max(prices)

        if max_price == min_price:
            return 1.0  # All same price

        # Invert score so lower price = higher score
        normalized = (max_price - price) / (max_price - min_price)
        return max(0.0, min(1.0, normalized))

    @staticmethod
    def _calculate_eviction_score(sku: Dict[str, Any]) -> float:
        """Calculate eviction score (0-1, higher is better)."""
        eviction_rate = sku.get("eviction_rate")
        if eviction_rate is None:
            return 0.3  # Penalty for unknown eviction rate

        # Convert to score (lower eviction = higher score)
        eviction_scores = {
            "0-5": 1.0,
            "5-10": 0.8,
            "10-15": 0.6,
            "15-20": 0.4,
            "20+": 0.2,
        }

        return eviction_scores.get(eviction_rate, 0.1)

    @staticmethod
    def _calculate_performance_score(
        sku: Dict[str, Any], all_skus: List[Dict[str, Any]]
    ) -> float:
        """Calculate performance score based on price per vCPU and price per GB."""
        price = sku.get("price")
        vcpus = sku.get("vcpus")
        memory_gb = sku.get("memory_gb")

        if (
            price is None
            or vcpus is None
            or memory_gb is None
            or not isinstance(vcpus, (int, float))
            or not isinstance(memory_gb, (int, float))
            or not isinstance(price, (int, float))
        ):
            return 0.5  # Neutral if missing data

        # Calculate price per compute unit (weighted combination of CPU and memory)
        compute_units = float(vcpus) + (
            float(memory_gb) / 4
        )  # 4GB memory ≈ 1 vCPU in value
        price_per_unit = float(price) / compute_units

        # Get all price per unit ratios for normalization
        ratios = []
        for s in all_skus:
            s_price = s.get("price")
            s_vcpus = s.get("vcpus")
            s_memory = s.get("memory_gb")
            if (
                s_price is not None
                and s_vcpus is not None
                and s_memory is not None
                and isinstance(s_price, (int, float))
                and isinstance(s_vcpus, (int, float))
                and isinstance(s_memory, (int, float))
            ):
                s_units = float(s_vcpus) + (float(s_memory) / 4)
                ratios.append(float(s_price) / s_units)

        if not ratios:
            return 0.5

        min_ratio = min(ratios)
        max_ratio = max(ratios)

        if max_ratio == min_ratio:
            return 1.0

        # Invert so lower price per unit = higher score
        normalized = (max_ratio - price_per_unit) / (max_ratio - min_ratio)
        return max(0.0, min(1.0, normalized))

    @staticmethod
    def _calculate_availability_score(
        sku: Dict[str, Any], all_skus: List[Dict[str, Any]]
    ) -> float:
        """Calculate availability score based on number of zones."""
        zones = sku.get("zones", [])
        zone_count = len(zones)

        # Get max zones for normalization
        max_zones = max(len(s.get("zones", [])) for s in all_skus)

        if max_zones == 0:
            return 0.0

        return zone_count / max_zones

    @staticmethod
    def _calculate_architecture_score(
        sku: Dict[str, Any], criteria: RecommendationCriteria
    ) -> float:
        """Calculate architecture score based on preferences."""
        architecture = sku.get("architecture")

        # If no preference, neutral score
        if criteria.architecture_preference is None:
            # Give slight bonus to ARM64 for better price/performance in general
            return 0.6 if architecture == "Arm64" else 0.5

        # Exact preference match
        if architecture == criteria.architecture_preference:
            return 1.0
        else:
            return 0.3  # Penalty for not matching preference
