// File: components/forms/ResumeBuilder.jsx
import React, { useState } from 'react';
import BasicsForm from '../forms/BasicsForm';            // <- fix casing
import ExperienceForm from '../forms/ExperienceForm';
import EducationForm from '../forms/EducationForm';
import CertificationsForm from '../forms/CertificationsForm';
import ProjectsForm from '../forms/ProjectsForm';
import PublicationsForm from '../forms/PublicationsForm';
import AwardsForm from '../forms/AwardsForm';            // <- fix var name
import SkillsForm from '../forms/SkillsForm';

import {
  initialBasics,          // <- make sure this exists (see below)
  initialExperience,
  initialEducation,
  initialCertificate,
  initialProject,
  initialPublication,
  initialAward,
  initialSkill
} from '../utils/defaultTemplates';

import '../styles/ResumeBuilder.css';

const API_BASE = process.env.REACT_APP_API_BASE ?? "http://localhost:8000";

// helpers
const toStringArray = (v) => {
  if (Array.isArray(v)) return v.map(x => String(x || "").trim()).filter(Boolean);
  if (typeof v === "string") return [v.trim()].filter(Boolean);
  return [];
};

const mergeUnique = (...lists) => {
  const out = [];
  const seen = new Set();
  for (const arr of lists) {
    for (const s of toStringArray(arr)) {
      if (!seen.has(s)) { seen.add(s); out.push(s); }
    }
  }
  return out;
};

// Map current form state into JSON Resume (tolerant / normalized)
// Map current form state into JSON Resume (tolerant / normalized)
function mapToJsonResume({
  basics = {},
  experience,
  education,
  certifications,
  projects,
  publications,
  awards,
  skills
}) {
  const safeBasics = {
    ...basics,
    location: basics.location ?? {
      address: "", city: "", region: "", postalCode: "", countryCode: ""
    },
    profiles: Array.isArray(basics.profiles) ? basics.profiles : []
  };

  return {
    basics: {
      name: safeBasics.name || "",
      label: safeBasics.label || "",
      email: safeBasics.email || "",
      phone: safeBasics.phone || "",
      url: safeBasics.url || "",
      summary: safeBasics.summary || "",
      location: {
        address: safeBasics.location.address || "",
        city: safeBasics.location.city || "",
        region: safeBasics.location.region || "",
        postalCode: safeBasics.location.postalCode || "",
        countryCode: safeBasics.location.countryCode || ""
      },
      // forms give strings; normalize to JSON Resume objects
      profiles: safeBasics.profiles.map(p =>
        typeof p === "string"
          ? { network: "", username: p, url: "" }
          : {
              network: p.network || "",
              username: p.username || "",
              url: p.url || ""
            }
      )
    },

    // EXPERIENCE -> work[]
    work: (experience || []).map(x => ({
      name: x.company || x.name || "",
      position: x.title || x.position || "",
      startDate: x.startDate || "",
      endDate: x.isCurrent ? "" : (x.endDate || ""),
      location: x.setting || "",                 // <- map "Remote/Hybrid/On-site"
      highlights: Array.isArray(x.description) ? x.description : []
    })),

    // EDUCATION -> education[]
    education: (education || []).map(ed => ({
      institution: ed.institution || "",
      studyType: ed.studyType || "",
      area: ed.area || "",
      score: ed.score || "",
      startDate: ed.startDate || "",
      endDate: ed.isCurrent ? "" : (ed.endDate || ""),
      description: Array.isArray(ed.description) ? ed.description : []
    })),

    // CERTIFICATES -> certificates[]
    certificates: (certifications || []).map(c =>
      typeof c === "string"
        ? { name: c, date: "", issuer: "" }
        : {
            name: c.name || "",
            date: c.date || "",
            issuer: c.issuer || "",
            url: c.url || ""
          }
    ),

    // PROJECTS -> projects[] (only fields you capture)
    projects: (projects || []).map(p =>
      typeof p === "string"
        ? { name: p }
        : {
            name: p.name || "",
            url: p.url || "",
            highlights: Array.isArray(p.highlights) ? p.highlights : []
          }
    ),

    // PUBLICATIONS -> publications[]
    publications: (publications || []).map(pub => ({
      name: pub.name || "",
      publisher: pub.publisher || "",
      releaseDate: pub.releaseDate || "",
      url: pub.url || "",
      summary: pub.summary || ""
    })),

    // AWARDS -> awards[]
    awards: (awards || []).map(a => ({
      title: a.title || "",
      awarder: a.awarder || "",
      date: a.date || "",
      summary: a.summary || ""
    })),

    // SKILLS -> skills[] (no keywords in form; omit)
    skills: (skills || [])
      .map((s) => (typeof s === "string" ? s.trim() : String(s?.name || "").trim()))
      .filter(Boolean)
      .map((name) => ({ name }))  // ← only { name }, no level
  };
}

const ResumeBuilder = () => {
  // ❗ basics should be an object, not an array
  const [basics, setBasics] = useState(initialBasics);

  // The rest are lists (multiple entries), keep as arrays
  const [experience, setExperience] = useState([initialExperience]);
  const [education, setEducation] = useState([initialEducation]);
  const [certifications, setCertifications] = useState([initialCertificate]);
  const [projects, setProjects] = useState([initialProject]);
  const [publications, setPublications] = useState([initialPublication]);
  const [awards, setAwards] = useState([initialAward]);
  const [skills, setSkills] = useState([initialSkill]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    const resume = mapToJsonResume({
      basics,                     // <- now an object
      experience,
      education,
      certifications,
      projects,
      skills
    });

    try {
      const res = await fetch(`${API_BASE}/resume/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: 'demo', resume }),
      });
      if (!res.ok) {
        const msg = await res.text().catch(() => '');
        throw new Error(msg || 'Failed to save resume');
      }
      const data = await res.json();
      alert(`Resume saved! v${data.version}`);
    } catch (err) {
      alert('Error saving resume');
    }
  };

  return (
    <form className="resume-form" onSubmit={handleSubmit}>
      <h2>Resume Builder</h2>

      <BasicsForm basics={basics} setBasics={setBasics} />
      <ExperienceForm experience={experience} setExperience={setExperience} />
      <EducationForm education={education} setEducation={setEducation} />
      <CertificationsForm certifications={certifications} setCertifications={setCertifications} />
      <ProjectsForm projects={projects} setProjects={setProjects} />
      <PublicationsForm publications={publications} setPublications={setPublications} />
      <AwardsForm awards={awards} setAwards={setAwards} />
      <SkillsForm skills={skills} setSkills={setSkills} />

      <br /><br />
      <button type="submit">Submit Resume</button>
    </form>
  );
};

export default ResumeBuilder;
