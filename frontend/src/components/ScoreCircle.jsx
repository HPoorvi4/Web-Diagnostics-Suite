// src/components/ScoreCircle.jsx
import React, { useEffect, useState } from "react";

const ScoreCircle = ({
  score,
  size = 120,
  strokeWidth = 8,
  title = "Score",
  animated = true,
}) => {
  const [animatedScore, setAnimatedScore] = useState(0);

  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (animatedScore / 100) * circumference;

  // Get color based on score
  const getScoreColor = (score) => {
    if (score >= 80) return "#10b981"; // green-500
    if (score >= 60) return "#f59e0b"; // amber-500
    if (score >= 40) return "#f97316"; // orange-500
    return "#ef4444"; // red-500
  };

  // Get score label
  const getScoreLabel = (score) => {
    if (score >= 90) return "Excellent";
    if (score >= 80) return "Good";
    if (score >= 60) return "Fair";
    if (score >= 40) return "Poor";
    return "Critical";
  };

  useEffect(() => {
    if (animated) {
      const timer = setTimeout(() => {
        setAnimatedScore(score);
      }, 100);
      return () => clearTimeout(timer);
    } else {
      setAnimatedScore(score);
    }
  }, [score, animated]);

  return (
    <div className="flex flex-col items-center">
      <div className="relative">
        <svg width={size} height={size} className="transform -rotate-90">
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="#e5e7eb"
            strokeWidth={strokeWidth}
            fill="transparent"
          />

          {/* Progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={getScoreColor(score)}
            strokeWidth={strokeWidth}
            fill="transparent"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{
              transition: animated
                ? "stroke-dashoffset 1s ease-in-out"
                : "none",
            }}
          />
        </svg>

        {/* Score text overlay */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="text-2xl font-bold"
            style={{ color: getScoreColor(score) }}
          >
            {Math.round(animatedScore)}
          </span>
          <span className="text-xs text-gray-500 uppercase tracking-wide">
            / 100
          </span>
        </div>
      </div>

      {/* Title and label */}
      <div className="text-center mt-2">
        <h3 className="text-sm font-medium text-gray-900">{title}</h3>
        <p
          className="text-xs font-medium mt-1"
          style={{ color: getScoreColor(score) }}
        >
          {getScoreLabel(score)}
        </p>
      </div>
    </div>
  );
};

export default ScoreCircle;
