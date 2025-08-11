// File: components/forms/ResumeBuilder.jsx
import React, { useState } from 'react';
import BasicsForm from '../forms/BasicsForm';
import ExperienceForm from '../forms/ExperienceForm';
import EducationForm from '../forms/EducationForm';
import CertificationsForm from '../forms/CertificationsForm';
import ProjectsForm from '../forms/ProjectsForm';
import SkillsForm from '../forms/SkillsForm';
import '../styles/ResumeBuilder.css';
import { initialExperience, initialEducation } from '../utils/defaultTemplates';

const API_BASE = process.env.REACT_APP_API_BASE ?? "http://localhost:8000"; // change to 5000 if that's your server

// Local default for Basics so the form has all JSON Resume fields available.
const initialBasics = {
  name: '',
  label: '',
  email: '',
  phone: '',
  url: '',
  summary: '',
  location: {
    address: '',
    city: '',
    region: '',
    postalCode: '',
    countryCode: '',
  },
  profiles: [] // e.g., [{ network: 'LinkedIn', username: 'you', url: '...' }]
};

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

// Map your current form state into JSON Resume (tolerant / normalized)
function mapToJsonResume({ basics = {}, experience, education, certifications, projects, skills }) {
  return {
    basics: {
      name: basics.name || "",
      label: basics.label || "",
      email: basics.email || "",
      phone: basics.phone || "",
      url: basics.url || "",
      // If you want to “remove summary”, keep it empty here or delete the key.
      summary: basics.summary || "",
      location: basics.location || {},
      profiles: Array.isArray(basics.profiles)
        ? basics.profiles.map(p => (
            typeof p === "string"
              ? { network: "", username: p, url: "" }
              : {
                  network: p.network || "",
                  username: p.username || "",
                  url: p.url || ""
                }
          ))
        : []
    },

    // EXPERIENCE -> JSON Resume "work"
    // Accepts: x.descriptions (preferred), x.description (string), x.highlights, x.bullets
    work: (experience || []).map(x => ({
      name: x.company || x.name || "",
      position: x.title || x.position || "",
      url: x.url || "",
      startDate: x.startDate || "",
      endDate: x.endDate || "",
      // If you want to drop summary, leave it blank or omit this line
      summary: x.summary || "",
      highlights: mergeUnique(
        x.descriptions,  // ← normalized list from your form
        x.description,   // ← sometimes a single textarea
        x.highlights,    // ← legacy
        x.bullets        // ← any other alias you used
      )
    })),

    // EDUCATION (ensure courses is a string array)
    education: (education || []).map(ed => ({
      institution: ed.institution || ed.school || "",
      url: ed.url || "",
      area: ed.area || ed.field || "",
      studyType: ed.studyType || ed.degree || "",
      startDate: ed.startDate || "",
      endDate: ed.endDate || "",
      score: ed.score || "",
      courses: toStringArray(ed.courses)
    })),

    // CERTIFICATES
    certificates: (certifications || []).map(c =>
      typeof c === "string"
        ? { name: c, date: "", issuer: "" }
        : { name: c.name || "", date: c.date || "", issuer: c.issuer || "", url: c.url || "" }
    ),

    // PROJECTS -> convert descriptions[] to highlights[]
    projects: (projects || []).map(p =>
      typeof p === "string"
        ? { name: p }
        : {
            name: p.name || "",
            startDate: p.startDate || "",
            endDate: p.endDate || "",
            description: p.description || "", // keep long prose if you want
            highlights: mergeUnique(p.descriptions, p.highlights, p.bullets),
            url: p.url || ""
          }
    ),

    // SKILLS -> ensure keywords is a string array
    skills: (skills || []).map(s =>
      typeof s === "string"
        ? { name: s, level: "", keywords: [] }
        : { name: s.name || "", level: s.level || "", keywords: toStringArray(s.keywords ?? s.items) }
    ),
  };
}

const ResumeBuilder = () => {
  const [basics, setBasics] = useState(initialBasics);
  const [experience, setExperience] = useState([initialExperience]);
  const [education, setEducation] = useState([initialEducation]);
  const [certifications, setCertifications] = useState([]);
  const [projects, setProjects] = useState([]);
  const [skills, setSkills] = useState([]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    // assemble the JSON Resume
    const resume = mapToJsonResume({
      basics,
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
        // TODO: replace "demo" with real authenticated user_id when you add auth
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
      // console.error(err);
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
      <SkillsForm skills={skills} setSkills={setSkills} />

      <br /><br />
      <button type="submit">Submit Resume</button>
    </form>
  );
};

export default ResumeBuilder;
