# FHIR Patient Imaging — Required Images & Open-Source Sources

10 medical images are needed across 8 patients (4 patients have no imaging: Margaret Chen, Thomas Reeves, George Nakamura).

All placeholder paths reference `file://data/images/<filename>`.

---

## Image Inventory

| # | Patient | Filename | Modality | Clinical Finding |
|---|---------|----------|----------|-----------------|
| 1 | James Wilson | `james-wilson-cxr.png` | CXR (PA) | RLL consolidation consistent with pneumonia |
| 2 | Linda Martinez | `linda-martinez-ct-abdomen.png` | CT Abdomen | 3.2cm pancreatic head mass, bile duct dilation, SMA abutment |
| 3 | Robert Thompson | `robert-thompson-histopath.png` | Histopathology (H&E) | Atypical melanocytic proliferation, spitzoid features, 7mm lesion |
| 4 | Doris Yamamoto | `doris-yamamoto-brain-mri.png` | Brain MRI (DWI) | Restricted diffusion left MCA territory |
| 5 | Baby Torres | `baby-torres-echo.png` | Echocardiogram (TTE) | Large perimembranous VSD, LV dilation |
| 6 | Sarah O'Brien | `sarah-obrien-fetal-us.png` | Fetal Ultrasound | Normal growth at 34+2 weeks, normal AFI |
| 7 | Marcus Williams | `marcus-williams-cardiac-mri.dcm` | Cardiac MRI | Asymmetric septal hypertrophy 25mm, SAM of mitral valve, no LGE |
| 8 | Patricia Johnson | `patricia-johnson-cxr.png` | CXR (AP portable) | Clear lungs, no pneumothorax (post-op baseline) |
| 9 | Patricia Johnson | `patricia-johnson-ct-chest.dcm` | CT PE protocol | Saddle PE at PA bifurcation, RV dilation (RV/LV 1.6) |
| 10 | David Kim | `david-kim-ct-chest.dcm` | CT Chest | 4.2cm spiculated RUL mass, mediastinal lymphadenopathy |

---

## Open-Source Image Sources

### 1. James Wilson — Chest X-ray (RLL Pneumonia)

**Wikimedia Commons (CC BY-SA)**
- Category: [X-rays of pneumonia](https://commons.wikimedia.org/wiki/Category:X-rays_of_pneumonia)
- Specific files:
  - `RLL pneumoniaM.jpg` — Right lower lobe pneumonia (frontal view)
  - `RLL pneumoniaLM.jpg` — Right lower lobe pneumonia (lateral view)
  - `X-ray of lobar pneumonia.jpg` — Lobar pneumonia
- License: CC BY-SA 3.0 / 4.0 (verify per file page)

**Radiopaedia (CC BY-NC-SA 3.0)**
- Case: [Right lower lobe consolidation - pneumonia](https://radiopaedia.org/cases/right-lower-lobe-consolidation-pneumonia)
- Downloadable: Yes

---

### 2. Linda Martinez — CT Abdomen (Pancreatic Head Mass)

**The Cancer Imaging Archive (TCIA) — CC BY 3.0/4.0**
- Collection: [PANCREATIC-CT-CBCT-SEG](https://www.cancerimagingarchive.net/collection/pancreatic-ct-cbct-seg/)
  - 40 patients with locally advanced pancreatic cancer, contrast-enhanced CT
  - DICOM format, free download, no registration required
- Collection: [Pancreas-CT](https://www.cancerimagingarchive.net/collection/pancreas-ct/)
  - 82 abdominal contrast-enhanced CT scans (NIH Clinical Center)
  - Note: This set is healthy/non-cancer controls — use PANCREATIC-CT-CBCT-SEG for tumor cases

**PMC Open Access**
- [Lung Cancer and Radiological Imaging (PMC8206195)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8206195/) — CC BY, includes abdominal CT examples

---

### 3. Robert Thompson — Histopathology (Spitzoid Melanocytic Lesion)

**Nature Scientific Data — CC BY 4.0**
- Dataset: [A Spitzoid Tumor dataset with clinical metadata and Whole Slide Images](https://www.nature.com/articles/s41597-023-02585-2)
  - Full whole-slide H&E images of spitzoid tumors
  - Downloadable dataset for research

**PMC Open Access — CC BY 4.0**
- [The Spectrum of Spitz Melanocytic Lesions (PMC9209745)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9209745/)
  - H&E histopathology figures of spitzoid lesions
- [Recognizing Histopathological Simulators of Melanoma (PMC9299949)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9299949/)
  - Spitz nevus H&E at scanning and high magnification

**Pathology Outlines**
- [Atypical Spitz Tumor](https://www.pathologyoutlines.com/topic/skintumormelanocyticatypicalspitz.html)
  - Reference H&E images (educational use)

---

### 4. Doris Yamamoto — Brain MRI DWI (Left MCA Stroke)

**Radiopaedia (CC BY-NC-SA 3.0)**
- Case: [Left MCA acute ischemic stroke](https://radiopaedia.org/cases/left-mca-acute-ischaemic-stroke) — DWI showing restricted diffusion, downloadable
- Case: [MCA stroke - evolution](https://radiopaedia.org/cases/mca-stroke-evolution) — DWI + evolution, downloadable
- Case: [Hyperacute MCA infarct with DWI/FLAIR mismatch](https://radiopaedia.org/cases/hyperacute-mca-infarct-with-dwiflair-mismatch) — downloadable
- Case: [Left MCA infarct](https://radiopaedia.org/cases/left-mca-infarct) — downloadable

**PMC Open Access**
- [Imaging of Cerebral Ischemia (PMC3864615)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3864615/) — CC BY, DWI examples
- [Imaging in Acute Stroke (PMC3088377)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3088377/) — CC BY, MCA territory DWI

---

### 5. Baby Torres — Echocardiogram (Perimembranous VSD)

**Congenital Cardiac Anesthesia Society (CCAS)**
- [VSD Echo Education](https://ccasociety.org/education/echoimage/vsd-echo/)
  - TTE and TEE echo clips of VSDs including parasternal long-axis views of membranous VSD
  - Educational use

**AHA Circulation — Open Access Figures**
- [Ventricular Septal Defects (Circulation)](https://www.ahajournals.org/doi/10.1161/circulationaha.106.618124)
  - Echocardiographic images of perimembranous VSD with color Doppler

**Wikimedia Commons**
- [Category:Echocardiography](https://commons.wikimedia.org/wiki/Category:Echocardiography)
  - Browse for VSD echo images (limited selection)

**Pediatric Echo Education**
- [pedecho.org — Fetal VSD](https://pedecho.org/library/fetal/Fet-VSD)

---

### 6. Sarah O'Brien — Fetal Ultrasound (34 weeks, normal)

**Wikimedia Commons (CC BY-SA)**
- Category: [Ultrasound images of human pregnancy](https://commons.wikimedia.org/wiki/Category:Ultrasound_images_of_human_pregnancy) — 279 files
- Category: [Ultrasound pictures by Wolfgang Moroder](https://commons.wikimedia.org/wiki/Category:Ultrasound_pictures_by_Wolfgang_Moroder) — large collection at various gestational ages
- Look for late third-trimester images (30-36 weeks)

**MedlinePlus (Public Domain)**
- [Ultrasound, normal fetus - profile view](https://medlineplus.gov/ency/imagepages/2263.htm)

---

### 7. Marcus Williams — Cardiac MRI (Hypertrophic Cardiomyopathy)

**PMC Open Access — CC BY 4.0**
- [Phenotypes of HCM: An illustrative review of MRI findings (PMC6269344)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6269344/)
  - SSFP cine MR images showing asymmetric septal hypertrophy
  - LGE images showing mid-wall enhancement patterns
  - **Best open-access source for HCM cardiac MRI**

**PMC Open Access**
- [Cardiac MR Imaging of HCM (PMC5891337)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5891337/)
  - Multiple MRI figures of HCM phenotypes

**Wikimedia Commons**
- [Hypertrophic Cardiomyopathy - Echocardiogram](https://commons.wikimedia.org/wiki/File:Hypertrophic_Cardiomyopathy_-_Echocardiogram_-_Sam.ogv) — echo video (not MRI, but relevant)

---

### 8. Patricia Johnson — Chest X-ray (Clear lungs, post-op)

**Wikimedia Commons (CC BY-SA)**
- Category: [Medical X-rays (images)](https://commons.wikimedia.org/wiki/Category:Medical_X-rays_(images))
- Look for normal/near-normal CXR images
- Any clear chest X-ray without focal pathology will work

**NIH ChestX-ray14 Dataset (CC BY 4.0)**
- [NIH Clinical Center CXR Dataset](https://nihcc.app.box.com/v/ChestXray-NIHCC)
  - 112,120 frontal-view chest X-rays from 30,805 patients
  - Includes "No Finding" labeled images — perfect for this use case

---

### 9. Patricia Johnson — CT Chest (Saddle Pulmonary Embolism)

**PMC Open Access — CC BY 4.0**
- [Saddle PE in Cancer Patients (PMC9800169)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9800169/)
  - CT angiography showing thrombus straddling PA bifurcation
  - Published by Thieme, CC BY license
  - **Best open-access source — includes labeled figure**

**CASE Journal — CC BY 4.0**
- [Saddle PE Detected by TTE](https://www.cvcasejournal.com/article/S2468-6441(23)00233-5/fulltext)
  - CT PA showing dilated main PA and saddle PE with bilateral emboli

**Radiopaedia (CC BY-NC-SA 3.0)**
- Case: [Saddle pulmonary embolism](https://radiopaedia.org/cases/saddle-pulmonary-embolism-27)
  - CT PA with RV strain signs, downloadable

---

### 10. David Kim — CT Chest (RUL Lung Mass, NSCLC)

**The Cancer Imaging Archive (TCIA) — CC BY 3.0/4.0**
- Collection: [NSCLC-Radiogenomics](https://www.cancerimagingarchive.net/collection/nsclc-radiogenomics/)
  - 211 NSCLC patients, CT + PET/CT, with tumor segmentations
  - Includes gene mutation data (EGFR relevant for this patient)
- Collection: [NSCLC-Radiomics](https://www.cancerimagingarchive.net/collection/nsclc-radiomics/)
  - 422 NSCLC patients, pretreatment CT with tumor delineations
- Collection: [LUNGCT-DIAGNOSIS](https://www.cancerimagingarchive.net/collection/lungct-diagnosis/)
  - Diagnostic contrast-enhanced CT, specifically lung adenocarcinoma
  - **Best match — adenocarcinoma focus**

**PMC Open Access**
- [Lung Cancer and Radiological Imaging (PMC8206195)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8206195/)
  - CT images of lung adenocarcinoma, CC BY

---

## License Summary

| Source | License | Commercial Use | Attribution Required |
|--------|---------|---------------|---------------------|
| Wikimedia Commons | CC BY-SA 3.0/4.0 | Yes | Yes |
| PMC / PubMed Central | CC BY 4.0 (most) | Yes | Yes |
| Radiopaedia | CC BY-NC-SA 3.0 | No (non-commercial) | Yes |
| TCIA | CC BY 3.0/4.0 (>95%) | Yes | Yes |
| Nature Scientific Data | CC BY 4.0 | Yes | Yes |
| NIH ChestX-ray14 | CC BY 4.0 | Yes | Yes |
| MedlinePlus | Public Domain | Yes | No |

---

## Download Priority

For quickest setup, prioritize these sources (all CC BY, easy single-image downloads):

1. **Wikimedia Commons** — CXR pneumonia (#1), normal CXR (#8), fetal US (#6)
2. **PMC articles** — Saddle PE (#9), HCM MRI (#7), brain DWI stroke (#4), histopath (#3)
3. **TCIA** — Pancreatic CT (#2), lung mass CT (#10) — requires browsing DICOM collections
4. **Radiopaedia** — Brain DWI stroke (#4) alternative — requires free account for download

---

## Image Directory Setup

```bash
mkdir -p docgemma-connect/data/images/

# After downloading, place files as:
# docgemma-connect/data/images/james-wilson-cxr.png
# docgemma-connect/data/images/linda-martinez-ct-abdomen.png
# docgemma-connect/data/images/robert-thompson-histopath.png
# docgemma-connect/data/images/doris-yamamoto-brain-mri.png
# docgemma-connect/data/images/baby-torres-echo.png
# docgemma-connect/data/images/sarah-obrien-fetal-us.png
# docgemma-connect/data/images/marcus-williams-cardiac-mri.dcm
# docgemma-connect/data/images/patricia-johnson-cxr.png
# docgemma-connect/data/images/patricia-johnson-ct-chest.dcm
# docgemma-connect/data/images/david-kim-ct-chest.dcm
```

## Notes

- For DICOM files (.dcm), convert to PNG for web display: `dcm2pniigz` or use Python `pydicom` + `PIL`
- TCIA collections are large — use their NBIA Data Retriever to download individual series
- Radiopaedia downloads may require a free account
- For the demo, any clinically plausible image of the correct modality/anatomy works — exact pathology match is ideal but not strictly required for showcasing the FHIR integration
