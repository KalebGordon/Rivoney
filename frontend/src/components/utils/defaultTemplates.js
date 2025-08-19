// File: utils/defaultTemplates.js
export const initialExperience = {
  company: '',
  title: '',
  startDate: '',
  endDate: '',
  setting: '',
  description: [''],
};

export const initialEducation = {
  school: '',
  degree: '',
  startDate: '',
  endDate: '',
  focusAreas: '',
  honors: '',
  description: [''],
};

export const initialCertificate = {
  name: '',
  date: '',
  issuer: '',
  url: ''
};

export const initialProject = {
  name: '',
  description: '',
  highlights: [''], // start with one bullet for UX
  url: ''
};

export const initialSkill = [""];

export const initialPublication = { 
  name: "", 
  publisher: "", 
  releaseDate: "", 
  url: "", 
  summary: "" 
};

export const initialAward = { 
  title: "", 
  date: "", 
  awarder: "", 
  summary: "" 
};

export const initialBasics = {
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
  profiles: [''] 
};