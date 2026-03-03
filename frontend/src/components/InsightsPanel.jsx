import { motion } from "framer-motion";
import { AlertCircle, TrendingUp, Award, Target, BookOpen, Heart, Lightbulb } from "lucide-react";

export default function InsightsPanel({ insights, loading }) {
  if (loading) {
    return (
      <div className="bg-slate-800 rounded-lg p-8 border border-slate-700">
        <div className="flex items-center justify-center gap-3">
          <div className="animate-spin w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full"></div>
          <p className="text-slate-400">Generating AI insights...</p>
        </div>
      </div>
    );
  }

  if (!insights) {
    return (
      <div className="bg-slate-800 rounded-lg p-8 border border-slate-700">
        <div className="flex items-center gap-3 mb-4">
          <Lightbulb className="w-6 h-6 text-yellow-400" />
          <p className="text-white font-semibold">No AI Insights Yet</p>
        </div>
        <p className="text-slate-400">Sync your GitHub data to generate AI insights</p>
      </div>
    );
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.05, delayChildren: 0.1 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.3 } },
  };

  return (
    <motion.div
      className="space-y-4"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="flex items-center gap-3 mb-6 pb-4 border-b border-slate-700">
        <div className="w-10 h-10 bg-gradient-to-br from-amber-400 to-amber-600 rounded-lg flex items-center justify-center">
          <span className="text-lg">💡</span>
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">AI Developer Profile Analysis</h2>
          <p className="text-slate-400 text-xs">Powered by Gemini • Comprehensive insights</p>
        </div>
      </motion.div>

      {/* Developer Level & Primary Domain */}
      <motion.div variants={itemVariants} className="grid grid-cols-2 gap-3">
        <div className="bg-gradient-to-br from-blue-900/40 to-blue-800/20 border border-blue-700/40 rounded-lg p-4">
          <p className="text-slate-400 text-xs mb-1 font-semibold">Developer Level</p>
          <p className="text-lg font-bold text-blue-300">{insights.developer_level || "N/A"}</p>
        </div>
        <div className="bg-gradient-to-br from-purple-900/40 to-purple-800/20 border border-purple-700/40 rounded-lg p-4">
          <p className="text-slate-400 text-xs mb-1 font-semibold">Primary Domain</p>
          <p className="text-lg font-bold text-purple-300 truncate">
            {insights.primary_domains?.length > 0 ? insights.primary_domains[0].split("-")[0].trim() : "N/A"}
          </p>
        </div>
      </motion.div>

      {/* Activity & Efficiency Analysis */}
      {insights.activity_analysis && (
        <motion.div variants={itemVariants} className="bg-slate-700/40 border border-slate-600/40 rounded-lg p-4">
          <h3 className="text-base font-semibold text-white mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-green-400" />
            Activity & Efficiency
          </h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="bg-slate-800/50 rounded p-2.5">
              <p className="text-slate-400 text-xs">Efficiency</p>
              <p className="text-green-300 font-bold text-sm">{insights.activity_analysis.efficiency_rating}</p>
            </div>
            <div className="bg-slate-800/50 rounded p-2.5">
              <p className="text-slate-400 text-xs">Consistency</p>
              <p className="text-blue-300 font-bold text-sm">{insights.activity_analysis.consistency}</p>
            </div>
            <div className="col-span-2 bg-slate-800/50 rounded p-2.5">
              <p className="text-slate-400 text-xs mb-1">Weekly Output</p>
              <p className="text-slate-200 text-xs">{insights.activity_analysis.weekly_output}</p>
            </div>
            <div className="col-span-2 bg-slate-800/50 rounded p-2.5">
              <p className="text-slate-400 text-xs mb-1">Activity Pattern</p>
              <p className="text-slate-200 text-xs">{insights.activity_analysis.pattern}</p>
            </div>
          </div>
        </motion.div>
      )}

      {/* Top Repositories */}
      {insights.top_repositories_used && insights.top_repositories_used.length > 0 && (
        <motion.div variants={itemVariants} className="bg-slate-700/40 border border-slate-600/40 rounded-lg p-4">
          <h3 className="text-base font-semibold text-white mb-3 flex items-center gap-2">
            <Award className="w-4 h-4 text-yellow-400" />
            Key Repositories Analyzed
          </h3>
          <div className="space-y-2">
            {insights.top_repositories_used.slice(0, 5).map((repo, idx) => (
              <p key={idx} className="text-slate-300 text-xs bg-slate-800/50 rounded p-2">
                <span className="text-yellow-300 font-bold">→</span> {repo}
              </p>
            ))}
          </div>
        </motion.div>
      )}

      {/* Core Strengths */}
      {insights.core_strengths && insights.core_strengths.length > 0 && (
        <motion.div variants={itemVariants} className="bg-green-900/30 border border-green-700/40 rounded-lg p-4">
          <h3 className="text-base font-semibold text-white mb-3 flex items-center gap-2">
            <span className="text-lg">✅</span> Core Strengths
          </h3>
          <div className="space-y-1.5">
            {insights.core_strengths.map((strength, idx) => (
              <p key={idx} className="text-slate-200 text-xs">
                <span className="text-green-400 font-bold">•</span> {strength}
              </p>
            ))}
          </div>
        </motion.div>
      )}

      {/* Areas to Improve */}
      {insights.areas_to_improve && (
        <motion.div variants={itemVariants} className="bg-orange-900/30 border border-orange-700/40 rounded-lg p-4">
          <h3 className="text-base font-semibold text-white mb-3 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-orange-400" />
            Areas to Improve
          </h3>
          
          {insights.areas_to_improve.technical_gaps && insights.areas_to_improve.technical_gaps.length > 0 && (
            <div className="mb-3">
              <p className="text-orange-300 text-xs font-bold mb-1.5">Technical Gaps</p>
              <div className="space-y-1">
                {insights.areas_to_improve.technical_gaps.map((gap, idx) => (
                  <p key={idx} className="text-slate-300 text-xs bg-slate-800/50 rounded p-1.5">
                    <span className="text-orange-400">→</span> {gap}
                  </p>
                ))}
              </div>
            </div>
          )}
          
          {insights.areas_to_improve.activity_concerns && insights.areas_to_improve.activity_concerns.length > 0 && (
            <div className="mb-3">
              <p className="text-orange-300 text-xs font-bold mb-1.5">Activity Observations</p>
              <div className="space-y-1">
                {insights.areas_to_improve.activity_concerns.map((concern, idx) => (
                  <p key={idx} className="text-slate-300 text-xs bg-slate-800/50 rounded p-1.5">
                    <span className="text-orange-400">→</span> {concern}
                  </p>
                ))}
              </div>
            </div>
          )}

          {insights.areas_to_improve.domain_specific && insights.areas_to_improve.domain_specific.length > 0 && (
            <div>
              <p className="text-orange-300 text-xs font-bold mb-1.5">Domain-Specific Growth</p>
              <div className="space-y-1">
                {insights.areas_to_improve.domain_specific.map((growth, idx) => (
                  <p key={idx} className="text-slate-300 text-xs bg-slate-800/50 rounded p-1.5">
                    <span className="text-orange-400">→</span> {growth}
                  </p>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Coding Discipline */}
      {insights.coding_discipline_explained && (
        <motion.div variants={itemVariants} className="bg-cyan-900/30 border border-cyan-700/40 rounded-lg p-4">
          <h3 className="text-base font-semibold text-white mb-2">📊 Coding Discipline</h3>
          <p className="text-cyan-300 font-bold text-sm mb-1.5">{insights.coding_discipline_explained.rating}</p>
          <p className="text-slate-300 text-xs mb-2">{insights.coding_discipline_explained.meaning}</p>
          <div className="bg-slate-800/50 rounded p-2.5 mb-2 border-l-2 border-cyan-500">
            <p className="text-slate-400 text-xs"><span className="text-cyan-300 font-semibold">Evidence:</span> {insights.coding_discipline_explained.evidence}</p>
          </div>
          <p className="text-slate-300 text-xs"><span className="text-cyan-300 font-semibold">Why it matters:</span> {insights.coding_discipline_explained.why_matters}</p>
          <p className="text-slate-400 text-xs mt-1.5"><span className="text-cyan-400 font-semibold">→ Improve:</span> {insights.coding_discipline_explained.improvement}</p>
        </motion.div>
      )}

      {/* Focus Style */}
      {insights.focus_style_explained && (
        <motion.div variants={itemVariants} className="bg-indigo-900/30 border border-indigo-700/40 rounded-lg p-4">
          <h3 className="text-base font-semibold text-white mb-2">🎯 Focus Style</h3>
          <p className="text-indigo-300 font-bold text-sm mb-1.5">{insights.focus_style_explained.style}</p>
          <p className="text-slate-300 text-xs mb-2">{insights.focus_style_explained.meaning}</p>
          <div className="bg-slate-800/50 rounded p-2.5 mb-2 border-l-2 border-indigo-500">
            <p className="text-slate-400 text-xs"><span className="text-indigo-300 font-semibold">Evidence:</span> {insights.focus_style_explained.evidence}</p>
          </div>
          <p className="text-slate-300 text-xs mb-1.5"><span className="text-indigo-300 font-semibold">Career Path:</span> {insights.focus_style_explained.career_implications}</p>
          <p className="text-slate-400 text-xs"><span className="text-indigo-400 font-semibold">→ Recommendation:</span> {insights.focus_style_explained.recommendation}</p>
        </motion.div>
      )}

      {/* Growth Opportunities */}
      {insights.growth_opportunities && (
        <motion.div variants={itemVariants} className="bg-pink-900/30 border border-pink-700/40 rounded-lg p-4">
          <h3 className="text-base font-semibold text-white mb-3 flex items-center gap-2">
            <Target className="w-4 h-4 text-pink-400" />
            Growth Opportunities
          </h3>
          
          {insights.growth_opportunities.next_skills && insights.growth_opportunities.next_skills.length > 0 && (
            <div className="mb-3">
              <p className="text-pink-300 text-xs font-bold mb-1.5">Skills to Learn</p>
              <div className="space-y-1.5">
                {insights.growth_opportunities.next_skills.map((skill, idx) => (
                  <p key={idx} className="text-slate-300 text-xs bg-slate-800/50 rounded p-1.5">
                    <span className="text-pink-400">→</span> {skill}
                  </p>
                ))}
              </div>
            </div>
          )}

          {insights.growth_opportunities.project_ideas && insights.growth_opportunities.project_ideas.length > 0 && (
            <div>
              <p className="text-pink-300 text-xs font-bold mb-1.5">Project Ideas</p>
              <div className="space-y-1.5">
                {insights.growth_opportunities.project_ideas.map((project, idx) => (
                  <p key={idx} className="text-slate-300 text-xs bg-slate-800/50 rounded p-1.5">
                    <span className="text-pink-400">💡</span> {project}
                  </p>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Learning Roadmap */}
      {insights.learning_roadmap && (
        <motion.div variants={itemVariants} className="bg-gradient-to-br from-violet-900/40 to-violet-800/20 border border-violet-700/40 rounded-lg p-4">
          <h3 className="text-base font-semibold text-white mb-3 flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-violet-400" />
            4-Month Learning Roadmap
          </h3>
          
          <div className="mb-3 p-2.5 bg-slate-800/50 rounded-lg border-l-3 border-violet-500">
            <p className="text-slate-400 text-xs font-semibold">Current Domain</p>
            <p className="text-violet-300 font-bold text-sm">{insights.learning_roadmap.current_domain}</p>
            <p className="text-slate-400 text-xs mt-1">Mastery Level: <span className="text-violet-400 font-semibold">{insights.learning_roadmap.domain_mastery_level}</span></p>
          </div>

          {/* Phase 1 */}
          {insights.learning_roadmap.phase_1_months_1_2 && (
            <div className="mb-2 p-2.5 bg-slate-800/40 rounded border-l-2 border-violet-400">
              <p className="text-slate-400 text-xs font-bold">Months 1-2: Deepen Current Domain</p>
              <p className="text-violet-300 font-semibold text-xs mt-0.5">{insights.learning_roadmap.phase_1_months_1_2.domain}</p>
              <p className="text-slate-300 text-xs mt-0.5">Goal: <span className="text-violet-400 font-semibold">{insights.learning_roadmap.phase_1_months_1_2.goal}</span></p>
              <p className="text-slate-400 text-xs mt-1">Why: {insights.learning_roadmap.phase_1_months_1_2.why}</p>
            </div>
          )}

          {/* Phase 2 */}
          {insights.learning_roadmap.phase_2_months_3_4 && (
            <div className="mb-2 p-2.5 bg-slate-800/40 rounded border-l-2 border-cyan-400">
              <p className="text-slate-400 text-xs font-bold">Months 3-4: Add Complementary Domain</p>
              <p className="text-cyan-300 font-semibold text-xs mt-0.5">{insights.learning_roadmap.phase_2_months_3_4.domain}</p>
              <p className="text-slate-300 text-xs mt-0.5">Goal: <span className="text-cyan-400 font-semibold">{insights.learning_roadmap.phase_2_months_3_4.goal}</span></p>
              <p className="text-slate-400 text-xs mt-1">Why: {insights.learning_roadmap.phase_2_months_3_4.why}</p>
            </div>
          )}

          {/* Phase 3 */}
          {insights.learning_roadmap.phase_3_months_5_6 && (
            <div className="mb-3 p-2.5 bg-slate-800/40 rounded border-l-2 border-pink-400">
              <p className="text-slate-400 text-xs font-bold">Months 5-6 (Optional)</p>
              <p className="text-pink-300 font-semibold text-xs mt-0.5">{insights.learning_roadmap.phase_3_months_5_6.domain}</p>
              <p className="text-slate-300 text-xs mt-0.5">Goal: <span className="text-pink-400 font-semibold">{insights.learning_roadmap.phase_3_months_5_6.goal}</span></p>
              <p className="text-slate-400 text-xs mt-1">Why: {insights.learning_roadmap.phase_3_months_5_6.why}</p>
            </div>
          )}

          {/* Implementation */}
          {insights.learning_roadmap.implementation && insights.learning_roadmap.implementation.length > 0 && (
            <div className="pt-2 border-t border-slate-600">
              <p className="text-slate-400 text-xs font-bold mb-1.5">How to Implement</p>
              <div className="space-y-1">
                {insights.learning_roadmap.implementation.map((tip, idx) => (
                  <p key={idx} className="text-slate-300 text-xs">
                    <span className="text-violet-400">✓</span> {tip}
                  </p>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Burnout Risk Assessment */}
      {insights.burnout_risk_assessment && (
        <motion.div 
          variants={itemVariants}
          className={`rounded-lg p-4 border ${
            insights.burnout_risk_assessment.risk_level === "Low"
              ? "bg-green-900/30 border-green-700/40"
              : insights.burnout_risk_assessment.risk_level === "Medium"
              ? "bg-yellow-900/30 border-yellow-700/40"
              : "bg-red-900/30 border-red-700/40"
          }`}
        >
          <h3 className="text-base font-semibold text-white mb-2 flex items-center gap-2">
            <Heart className="w-4 h-4" />
            Burnout Risk Assessment
          </h3>
          <p className={`text-sm font-bold mb-2 ${
            insights.burnout_risk_assessment.risk_level === "Low"
              ? "text-green-400"
              : insights.burnout_risk_assessment.risk_level === "Medium"
              ? "text-yellow-400"
              : "text-red-400"
          }`}>
            {insights.burnout_risk_assessment.risk_level} Risk
          </p>
          <p className="text-slate-300 text-xs mb-2">{insights.burnout_risk_assessment.explanation}</p>
          <p className="text-slate-400 text-xs mb-1.5">
            <span className="font-semibold">Meaning:</span> {
              insights.burnout_risk_assessment["if_" + insights.burnout_risk_assessment.risk_level.toLowerCase()] || "Monitor your patterns"
            }
          </p>
          <p className="text-slate-400 text-xs">
            <span className="font-semibold">Recommendation:</span> {insights.burnout_risk_assessment.recommendation}
          </p>
        </motion.div>
      )}

      {/* Comprehensive Assessment */}
      {insights.comprehensive_assessment && (
        <motion.div variants={itemVariants} className="bg-gradient-to-r from-amber-900/40 to-orange-900/30 border border-amber-700/40 rounded-lg p-4">
          <h3 className="text-base font-semibold text-white mb-3">📋 Comprehensive Assessment</h3>
          <p className="text-slate-200 leading-relaxed text-xs">
            {insights.comprehensive_assessment}
          </p>
        </motion.div>
      )}

      {/* Footer */}
      <motion.div variants={itemVariants} className="text-center text-slate-500 text-xs pt-4 border-t border-slate-700">
        <p>Generated by Gemini AI • {insights.generated_at ? new Date(insights.generated_at).toLocaleDateString() : "Just now"}</p>
      </motion.div>
    </motion.div>
  );
}
