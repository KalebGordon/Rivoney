// File: components/forms/ResumeBuilder.jsx
import React, { useState } from 'react';
import ExperienceForm from '../forms/ExperienceForm';
import EducationForm from '../forms/EducationForm';
import CertificationsForm from '../forms/CertificationsForm';
import ProjectsForm from '../forms/ProjectsForm';
import SkillsForm from '../forms/SkillsForm';
import '../styles/ResumeBuilder.css';
import { initialExperience, initialEducation } from '../utils/defaultTemplates';

const API_BASE = process.env.REACT_APP_API_BASE ?? "http://localhost:8000"; // change to 5000 if that's your server

// Map your current form state into JSON Resume (tolerant to strings or objects)
function mapToJsonResume({ basics = {}, experience, education, certifications, projects, skills }) {
  return {
    basics: {
      name: basics.name || "",
      label: basics.label || "",
      email: basics.email || "",
      phone: basics.phone || "",
      url: basics.url || "",
      summary: basics.summary || "",
      location: basics.location || {},
      profiles: basics.profiles || []
    },
    work: (experience || []).map(x => ({
      name: x.company || x.name || "",
      position: x.title || x.position || "",
      url: x.url || "",
      startDate: x.startDate || "",
      endDate: x.endDate || "",
      summary: x.summary || "",
      highlights: Array.isArray(x.highlights) ? x.highlights : []
    })),
    education: (education || []).map(ed => ({
      institution: ed.institution || ed.school || "",
      url: ed.url || "",
      area: ed.area || ed.field || "",
      studyType: ed.studyType || ed.degree || "",
      startDate: ed.startDate || "",
      endDate: ed.endDate || "",
      score: ed.score || "",
      courses: Array.isArray(ed.courses) ? ed.courses : []
    })),
    certificates: (certifications || []).map(c =>
      typeof c === "string"
        ? { name: c, date: "", issuer: "" }
        : { name: c.name || "", date: c.date || "", issuer: c.issuer || "", url: c.url || "" }
    ),
    projects: (projects || []).map(p =>
      typeof p === "string"
        ? { name: p }
        : {
            name: p.name || "",
            startDate: p.startDate || "",
            endDate: p.endDate || "",
            description: p.description || "",
            highlights: Array.isArray(p.highlights) ? p.highlights : [],
            url: p.url || ""
          }
    ),
    skills: (skills || []).map(s =>
      typeof s === "string"
        ? { name: s, level: "", keywords: [] }
        : { name: s.name || "", level: s.level || "", keywords: Array.isArray(s.keywords) ? s.keywords : [] }
    ),
    // you can add other JSON Resume sections later (awards, publications, etc.)
  };
}

const ResumeBuilder = () => {
  // if you have a BasicsForm, add basics state too
  const [experience, setExperience] = useState([initialExperience]);
  const [education, setEducation] = useState([initialEducation]);
  const [certifications, setCertifications] = useState([]);
  const [projects, setProjects] = useState([]);
  const [skills, setSkills] = useState([]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    // assemble the JSON Resume
    const resume = mapToJsonResume({
      // basics, // uncomment when you add a BasicsForm
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

      {/* Add a BasicsForm later to capture JSON Resume "basics" */}
      {/* <BasicsForm basics={basics} setBasics={setBasics} /> */}

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
