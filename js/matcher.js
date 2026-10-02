// SkillMatch — Core Matching Engine
// Adapted from India Runs main.py (score_candidate, check_honeypot, reasoning generation)
// Re-engineered for student-to-opportunity matching

/**
 * Calculate days until deadline
 */
function getDaysUntilDeadline(deadlineStr) {
  const deadline = new Date(deadlineStr);
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  deadline.setHours(0, 0, 0, 0);
  return Math.ceil((deadline - now) / (1000 * 60 * 60 * 24));
}

/**
 * Get deadline badge metadata (mirrors India Runs urgency logic)
 */
function getDeadlineBadge(deadlineStr) {
  const days = getDaysUntilDeadline(deadlineStr);
  if (days < 0)  return { text: "Closed",          cls: "badge-closed",    urgent: false, pulse: false };
  if (days === 0) return { text: "Closes TODAY 🔥", cls: "badge-critical",  urgent: true,  pulse: true  };
  if (days === 1) return { text: "1 day left 🔥",   cls: "badge-critical",  urgent: true,  pulse: true  };
  if (days <= 3)  return { text: `${days}d left 🔥`, cls: "badge-urgent",   urgent: true,  pulse: true  };
  if (days <= 7)  return { text: `${days} days left`, cls: "badge-warning", urgent: false, pulse: false };
  return              { text: `${days} days`,       cls: "badge-safe",     urgent: false, pulse: false };
}

/**
 * Main matching function — core of the platform
 * Adapted from score_candidate() in main.py
 * Returns detailed match breakdown for explainability
 */
function matchStudentToOpportunity(student, opportunity) {
  let score = 0;
  let maxScore = 0;
  let matchedSkills = [];
  let missingSkills = [];
  let bonusSkills = [];
  let reasons = [];
  let penalties = [];
  let eligible = true;
  let eligibilityIssues = [];

  const studentSkillsLower = (student.skills || []).map(s => s.toLowerCase().trim());

  // === REQUIRED SKILLS MATCHING (core, from India Runs keyword scoring) ===
  const reqWeight = 15;
  for (const reqSkill of opportunity.requiredSkills) {
    maxScore += reqWeight;
    // Fuzzy match: exact + substring
    const matched = studentSkillsLower.some(s =>
      s === reqSkill.toLowerCase() ||
      s.includes(reqSkill.toLowerCase()) ||
      reqSkill.toLowerCase().includes(s)
    );
    if (matched) {
      score += reqWeight;
      matchedSkills.push(reqSkill);
    } else {
      missingSkills.push(reqSkill);
    }
  }

  // === NICE-TO-HAVE SKILLS (bonus, diminishing weight) ===
  for (const niceSkill of (opportunity.niceToHaveSkills || [])) {
    const matched = studentSkillsLower.some(s =>
      s === niceSkill.toLowerCase() ||
      s.includes(niceSkill.toLowerCase()) ||
      niceSkill.toLowerCase().includes(s)
    );
    if (matched) {
      score += 5;
      maxScore += 5;
      bonusSkills.push(niceSkill);
    }
  }

  // === YEAR ELIGIBILITY (from India Runs experience range scoring) ===
  maxScore += 20;
  if (opportunity.eligibleYears.includes(Number(student.year))) {
    score += 20;
  } else {
    eligible = false;
    eligibilityIssues.push(
      `Requires Year ${opportunity.eligibleYears.join('/')} — you're in Year ${student.year}`
    );
  }

  // === BRANCH ELIGIBILITY ===
  maxScore += 15;
  const branchMatch =
    opportunity.eligibleBranches.includes('All') ||
    opportunity.eligibleBranches.includes(student.branch);
  if (branchMatch) {
    score += 15;
  } else {
    eligible = false;
    eligibilityIssues.push(
      `Branch not eligible — requires: ${opportunity.eligibleBranches.join(', ')}`
    );
  }

  // === CGPA CHECK (from India Runs services company penalty logic) ===
  maxScore += 10;
  const cgpa = parseFloat(student.cgpa) || 0;
  const minCGPA = opportunity.minCGPA || 0;
  if (minCGPA === 0 || cgpa >= minCGPA) {
    score += 10;
  } else {
    eligible = false;
    eligibilityIssues.push(`CGPA ${cgpa} below minimum ${minCGPA}`);
    penalties.push(`CGPA below minimum by ${(minCGPA - cgpa).toFixed(1)} points`);
  }

  // === INTEREST ALIGNMENT ===
  maxScore += 10;
  const oppTagsLower = (opportunity.tags || []).map(t => t.toLowerCase());
  const studentInterestsLower = (student.interests || []).map(i => i.toLowerCase());
  let interestMatch = [];
  for (const interest of studentInterestsLower) {
    const key = interest.split('/')[0]; // "AI/ML" → "AI"
    if (oppTagsLower.some(t => t.includes(key) || key.includes(t))) {
      interestMatch.push(interest);
    }
  }
  if (interestMatch.length > 0) {
    score += Math.min(10, interestMatch.length * 4);
  }

  // === CALCULATE MATCH PERCENTAGE ===
  const rawPct = maxScore > 0 ? (score / maxScore) * 100 : 0;
  // Apply eligibility penalty — ineligible opps capped at 60%
  const percentage = eligible
    ? Math.min(99, Math.round(rawPct))
    : Math.min(60, Math.round(rawPct * 0.7));

  // === GENERATE EXPLAINABLE REASONS (key PS-09 differentiator) ===
  // Mirrors India Runs reasoning string generation
  if (matchedSkills.length === opportunity.requiredSkills.length) {
    reasons.push(`✅ You have ALL ${matchedSkills.length} required skills`);
  } else if (matchedSkills.length > 0) {
    reasons.push(`✅ Matched ${matchedSkills.length}/${opportunity.requiredSkills.length} required skills: ${matchedSkills.slice(0, 3).join(', ')}`);
  }

  if (bonusSkills.length > 0) {
    reasons.push(`⭐ Bonus: You also have ${bonusSkills.slice(0, 3).join(', ')}`);
  }

  if (eligibilityIssues.length === 0) {
    reasons.push(`✅ You meet all eligibility criteria (Year, Branch, CGPA)`);
  }

  if (interestMatch.length > 0) {
    reasons.push(`🎯 Aligns with your interest in ${interestMatch[0]}`);
  }

  if (missingSkills.length > 0 && missingSkills.length <= 2) {
    reasons.push(`📚 Learn ${missingSkills.join(', ')} to boost your match`);
  }

  // Score category label
  let matchLabel = "Low Match";
  let matchColor = "#ef4444";
  if (percentage >= 85) { matchLabel = "Excellent Match"; matchColor = "#10b981"; }
  else if (percentage >= 70) { matchLabel = "Strong Match"; matchColor = "#22c55e"; }
  else if (percentage >= 55) { matchLabel = "Good Match"; matchColor = "#f59e0b"; }
  else if (percentage >= 40) { matchLabel = "Fair Match"; matchColor = "#f97316"; }

  return {
    score,
    maxScore,
    percentage,
    matchLabel,
    matchColor,
    matchedSkills,
    missingSkills,
    bonusSkills,
    reasons,
    penalties,
    eligible,
    eligibilityIssues,
    interestMatch,
    daysLeft: getDaysUntilDeadline(opportunity.deadline),
    deadlineBadge: getDeadlineBadge(opportunity.deadline)
  };
}

/**
 * Rank all opportunities for a student
 * Mirrors India Runs candidates.sort() logic
 */
function rankOpportunities(student, opportunities) {
  return opportunities
    .map(opp => ({
      ...opp,
      match: matchStudentToOpportunity(student, opp)
    }))
    .sort((a, b) => {
      // Eligible first (like India Runs honeypot exclusion)
      if (a.match.eligible && !b.match.eligible) return -1;
      if (!a.match.eligible && b.match.eligible) return 1;
      // Then by match %
      if (b.match.percentage !== a.match.percentage) {
        return b.match.percentage - a.match.percentage;
      }
      // Tiebreak by urgency (fewer days = more urgent)
      return a.match.daysLeft - b.match.daysLeft;
    });
}

/**
 * Filter opportunities by type, skill, and search query
 */
function filterOpportunities(rankedOpps, { type, skill, search, yearFilter }) {
  return rankedOpps.filter(opp => {
    if (type && type !== 'all' && opp.typeKey !== type) return false;

    if (skill) {
      const skillLower = skill.toLowerCase();
      const hasSkill =
        opp.requiredSkills.some(s => s.toLowerCase().includes(skillLower)) ||
        (opp.niceToHaveSkills || []).some(s => s.toLowerCase().includes(skillLower));
      if (!hasSkill) return false;
    }

    if (search) {
      const q = search.toLowerCase();
      const searchable = `${opp.title} ${opp.org} ${opp.description} ${opp.tags.join(' ')}`.toLowerCase();
      if (!searchable.includes(q)) return false;
    }

    return true;
  });
}

/**
 * Get skill gap for a specific opportunity (PS-09 stretch goal)
 * Returns radar chart data and gap list
 */
function getSkillGap(student, opportunity) {
  const allSkills = [
    ...opportunity.requiredSkills,
    ...(opportunity.niceToHaveSkills || []).slice(0, 3)
  ];

  const studentSkillsLower = (student.skills || []).map(s => s.toLowerCase());
  const gapData = allSkills.map(skill => {
    const has = studentSkillsLower.some(s =>
      s === skill.toLowerCase() || s.includes(skill.toLowerCase())
    );
    return {
      skill,
      has,
      required: opportunity.requiredSkills.includes(skill),
      score: has ? 100 : 0
    };
  });

  return gapData;
}
