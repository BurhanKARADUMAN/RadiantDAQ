# RadiantDAQ Phase 1 - Independent Dataset Audit and Scientific Interpretation
**Evidence:** Direct inspection and recalculation from the user-uploaded `RadiantDAQ_Phase1_Results_2026.zip`.  
**Scope:** GATE 9.4 / Geant4 geant4-11-02-patch-02 gamma transport; ideal, aligned 511-keV photons and 3 x 3 mm crystal cross-sections.  
**Status:** Successful independent CSV and macro-level reanalysis; raw ROOT and DoseActor RAW data were **not** included in the submitted archive.

## 1. Headline findings
- 18 independent-seed runs; six material-thickness conditions; 5,000 primaries per run; 90,000 new primaries in total.
- All 18 event-energy CSVs independently reproduce reported hit counts, near-full-energy counts and energy sums within numerical precision.
- Every new `run.mac` is **identical to its embedded `pilot_original_run.mac` except for the actual random-seed command**. Original commented header seed values remain stale; executable command and recorded metadata agree.
- All new `validated.json` records report successful ROOT Hits and DoseActor comparisons, but this review cannot re-read ROOT / RAW files absent from the archive.
- BGO exceeds LSO in interaction and near-full-energy deposition under all three tested conditions. This does not rank optical, SiPM, energy-resolution, or CTR performance.

## 2. Independently checked pooled results
|Material|Thickness|Events|Interacting / events|Interacting (%)|490-520 keV / events|Near-full (%)|Wilson 95% CI near-full (%)|Near-full between-seed SD (pp)|
|---|---:|---:|---:|---:|---:|---:|---|---:|
|BGO|10 mm|15000|8957|59.713|5336|35.573|34.811 - 36.343|0.809|
|LSO|10 mm|15000|8386|55.907|4356|29.040|28.319 - 29.772|0.596|
|BGO|20 mm|15000|12464|83.093|7622|50.813|50.013 - 51.613|0.624|
|LSO|20 mm|15000|12071|80.473|6377|42.513|41.724 - 43.306|0.643|
|BGO|30 mm|15000|13879|92.527|8336|55.573|54.777 - 56.367|1.052|
|LSO|30 mm|15000|13616|90.773|7172|47.813|47.015 - 48.613|0.435|

**Definition:** interacting = per-primary crystal Edep > 1e-6 keV. Near-full = 490 <= crystal Edep <= 520 keV. All fractions use *all incident gamma histories* as denominator, including zero-energy histories.

## 3. BGO-LSO contrasts
|Thickness|Interaction advantage (pp)|Approx. 95% CI (pp)|Near-full advantage (pp)|Approx. 95% CI (pp)|
|---|---:|---|---:|---|
|10 mm|+3.807|+2.690 to +4.924|+6.533|+5.478 to +7.589|
|20 mm|+2.620|+1.747 to +3.493|+8.300|+7.175 to +9.425|
|30 mm|+1.753|+1.128 to +2.379|+7.760|+6.632 to +8.888|

**Important:** Unadjusted normal (Wald) two-sample confidence intervals conditional on independent simulated histories. No multiple-testing correction. They do not represent uncertainty in Geant4 cross sections, cuts, crystal composition, or other modeling choices.

## 4. Audit checks and provenance
- **18/18 event datasets:** 5,000 numeric records each, total 90,000; event count / interaction / near-full / Edep-sum agreement passed.
- **18/18 macros:** exact pilot-copied command set, differing only by `/gate/random/setEngineSeed`; all 18 seed values are distinct.
- **18/18 provided ROOT SHA-256 strings** are distinct; actual ROOT bytes not present for independent rehashing.
- **ROOT-DoseActor recorded agreement:** maximum absolute discrepancy 0.00009131 MeV; maximum relative discrepancy 6.89e-08. These figures come from exported per-run validation records, not fresh raw-file recalculation.
- **Largest exported per-primary Edep:** 511.00002881 keV; no event exceeds 511.1 keV. This is not full energy conservation accounting.
- **Material database SHA-256** consistent in all run input records: `3ad9c0993b48af4bd573be9e976b636fd93c4c33350abf76879542830548b850`. No independent historical material DB checksum was supplied.
- **Software logs:** GATE 9.4 on Geant4 `geant4-11-02-patch-02`. All 18 GATE logs have the same hash, consistent with initialization-focused log content; distinct event CSV counts and recorded ROOT hashes were separately checked.

## 5. Pilot vs new: descriptive comparison
|Material|mm|Pilot near-full (%)|New near-full (%)|New minus pilot (pp)|
|---|---:|---:|---:|---:|
|BGO|10|35.760|35.573|-0.187|
|LSO|10|29.420|29.040|-0.380|
|BGO|20|51.960|50.813|-1.147|
|LSO|20|43.460|42.513|-0.947|
|BGO|30|55.980|55.573|-0.407|
|LSO|30|47.360|47.813|+0.453|

These six differences are modest (absolute largest 1.147 pp, BGO 20 mm) and the pilot trend is preserved. This is *consistency*, not a validated statistical equivalence test. The archived original pilot ROOT data, original material database hash and original GATE run-environment information should be independently audited before pooling the pilot with new runs.

## 6. Between-seed variability
The largest observed near-full replicate SD is 1.052 pp for BGO 30 mm (vs binomial run SD expected 0.703 pp, ratio of empirical to expected variance 2.244). With **only three replicates**, this does not establish extra systematic variability. Other ratio values range from 0.379 to 1.429 for near-full except that BGO 30 mm outlier; see `pooled_metrics.csv` in the original archive. Statistical variance alone cannot quantify model-form systematic uncertainty.

## 7. Possible spectral feature: 400-440 keV
- BGO: 726 of 45,000 simulated incident histories (1.613%).
- LSO: 4 of 45,000 simulated incident histories (0.009%).
- Plausible explanation: escape of high-Z material characteristic X rays following photoelectric interactions. **Not established:** step `processName` labels alone are not sufficient to trace the actual escaping secondary; track-level escape analysis, particle creation and boundary crossing are needed.

## 8. Evidence levels and limitations
1. **Verified in this review:** event-level CSV recalculation, macro comparison, seed uniqueness, reported per-run metrics, reconstructed plots, and numeric checks.
2. **Supported by supplied validators, not raw-file independently replicated:** ROOT Hits tree content, ROOT-to-DoseActor agreement, process step counts, original ROOT SHA digests.
3. **Not established:** full-system energy conservation, causal classification of escaped X rays, exact pilot environment equivalence, sensor/optical energy and timing performance, real PET sensitivity, experimental validation.
4. BGO interaction superiority is for the **specified mono-directional incident gamma geometry**. It is not proof that BGO yields a better overall scintillation detector, TOF-PET module or clinical system.

## 9. Recommended next actions
1. Preserve all original ROOT and `.mhd/.raw` scoring files on WSL, and archive hashes, versions, material DB and macros separately. Do not modify the pilot dataset.
2. Create a transport-validation extension that scores outgoing secondary photons/electrons and associates them with initial energy-deposition and escaping X-ray candidates.
3. Check sensitivity to EM physics list, production cuts, beam position / direction, material definitions, source parameters and geometry. Reference NIST XCOM separately for gamma attenuation plausibility.
4. Only after transport checks, implement optical scintillation production/transport, calibrated surface interactions and optical photon arrival timing; then incorporate a parameter-grounded SiPM model and electronics.
5. Before publication, make comments showing the seed in the macro headers consistent with the actual seed command; preserve the original archival copies unchanged.

## Source files
- `RadiantDAQ_Phase1_Results_2026.zip`, submitted 2026-11-15 (157 files; 18-run derived CSVs, macros, logs and validation JSONs; ROOT and RAW excluded).
- GitHub pilot baseline: https://github.com/BurhanKARADUMAN/RadiantDAQ/commit/3a10db4d1519cf97e1dad898b0bb21dbad4a1ec5
- Author: AI-assisted reanalysis; this report makes no claim of laboratory measurements or independent ROOT-level rerun.
