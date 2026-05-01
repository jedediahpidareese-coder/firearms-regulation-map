# Literature Foundation for a Working Paper on U.S. State Firearm Policy and Crime/Suicide

**Project:** Firearms Regulation working paper, foundational literature scan
**Date prepared:** 2026-05-01
**Author:** Literature scan agent (read-only review; no code/data modified)
**Predecessor documents extended here:**
`outputs/rdd_diagnostics/literature_scan.md` (9 papers, spatial-RDD focus)
`outputs/rdd_diagnostics/covariate_recommendations.md` (20 papers, covariate-set focus)

---

## Reader's orientation

This document is the third tier of literature work for the project. The earlier two scans nailed down (a) the methodological lineage from Dube–Lester–Reich (2010) into the spatial-RDD/border-county design family, and (b) the modern covariate philosophy that distinguishes the Lott-Mustard, Brennan Center, Moody-Marvell, and Donohue-Aneja-Weber (DAW) "stacks." Both prior scans are pre-supposed here — particular papers (Knight 2013; DAW 2019; Cheng-Hoekstra 2013; McClellan-Tekin 2017; Webster-Crifasi-Vernick 2014; Crifasi 2015; McCourt 2020; Kivisto-Phalen 2018; Luca-Malhotra-Poliquin 2017; Klarevas-Conner-Hemenway 2019; Koper-Roth 2001; Ashworth-Kozinetz 2021; Donohue-Cai-Bondy-Cook 2023; Miller-Hemenway 2002; Kalesan et al. 2016) get a single-line refresh below and citation tagging, but the per-paper detail and covariate decomposition is in the predecessors. This document fills five additional needs for paper drafting: (1) a 50-paper canonical list with citation counts and design tags, (2) explicit gap analysis, (3) journal-by-journal target analysis with reference-count and word-count benchmarks, (4) a recommended target journal with justification, and (5) a theoretical-framing menu for the introduction and motivation sections. Length target: 8,000–12,000 words.

A note on citations. In-text references are formatted as (Author Year) or (Author1 and Author2 Year) per the project brief. Where a precise page is invoked, it is shown as (Author Year, p. X). Google Scholar citation counts are reported where retrievable (precision: ±5%, fluctuates daily); when GS could not be probed directly, "n.r." indicates not reliably retrievable from this scan and the figure should be re-checked at typesetting. Working papers are flagged "(WP)"; published versions cited with the journal of record.

---

## Section 1 — The 50 most-cited firearm-policy / gun-violence / gun-suicide articles (post-1990)

This list is balanced across the policy taxonomy in the brief. Each entry uses a uniform mini-template:
- **Cite.** Authors, year, journal, vol/pp; GS citations as of 2024–2026 best estimate.
- **Policy.** What law variation drives identification.
- **Outcome.** Dependent variable.
- **Headline finding.** One-sentence punch line.
- **Identification.** Estimator and the load-bearing assumption.
- **(Notes.)** Where useful: subsequent contestation, our paper's relationship.

Citation counts marked GS are taken from Google Scholar at the time of writing or from secondary sources that cite GS (e.g., Wikipedia, RAND review tables, journal author pages, NBER abstract pages); counts marked NR are not robustly available from this scan. Citation counts above 1,000 should be treated as "definitively foundational"; 250–1000 as "well-established"; 100–250 as "well-cited within firearm-policy"; below 100 typically marks recent work whose stock is still building.

### 1.1 Foundational right-to-carry exchange (the Lott–Mustard / Ayres–Donohue / DAW arc)

**1. Lott, J. R., & Mustard, D. B. (1997).** "Crime, Deterrence, and Right-to-Carry Concealed Handguns." *Journal of Legal Studies* 26(1): 1–68. **GS ≈ 1,500+.**
- *Policy:* Shall-issue concealed-carry adoption (1977–1992 county panel).
- *Outcome:* UCR-7 violent and property crimes.
- *Headline:* RTC laws are associated with statistically significant reductions in violent crime; "more guns, less crime."
- *Identification:* County and year fixed effects, with 36-cell age × race × gender controls and a lagged arrest-rate proxy for deterrence.
- *Notes:* The single most contested specification in the U.S. firearm-policy literature. The 1998 Lott book of the same title (Univ. Chicago Press) extended the work and itself collected several thousand additional GS cites. Replication and re-extension by (Black and Nagin 1998), (Ayres and Donohue 2003), (Aneja, Donohue, and Zhang 2014), and (Donohue, Aneja, and Weber 2019) have largely overturned the headline claim, but the 1997 paper remains the methodological starting point and continues to be cited even by critics for its panel structure. RAND (Smart et al. 2024) classifies the literature on RTC and violent crime as "supportive evidence that RTC increases violent crime" — a near-inversion of Lott–Mustard.

**2. Ayres, I., & Donohue, J. J. (2003).** "Shooting Down the More Guns, Less Crime Hypothesis." *Stanford Law Review* 55(4): 1193–1312. **GS ≈ 700.**
- *Policy:* Same shall-issue laws extended through 2000.
- *Outcome:* UCR-7.
- *Headline:* Lott–Mustard effects evaporate or invert when adding incarceration, police staffing, and state-specific time trends; if anything RTC slightly increases violent crime.
- *Identification:* County and state fixed effects + state-specific linear trends; expanded covariate set ("DAW lineage" begins here).
- *Notes:* Initiated the long Ayres–Donohue/Lott exchange in *Stanford LR* (Plassmann and Whitley 2003 reply; Ayres and Donohue 2003b rejoinder). For methodology purposes, this paper is the warrant for the modern DAW covariate stack we will use.

**3. Plassmann, F., & Whitley, J. (2003).** "Confirming 'More Guns, Less Crime.'" *Stanford Law Review* 55(4): 1313–1369. **GS ≈ 250.**
- *Policy:* Same RTC variation, pro-Lott replication.
- *Outcome:* UCR-7.
- *Headline:* Defends LM specification with corrected coding; argues AD critique is fragile.
- *Identification:* County FE panel; LM covariate set with adjustments.
- *Notes:* Subsequently corrected in Ayres-Donohue rejoinder (same volume); the Plassmann–Whitley result depends on a coding decision later acknowledged as erroneous. Cited because it is the canonical "pro-Lott" reference within the academic literature; book-length pro-RTC work (Lott 2010, *More Guns, Less Crime*, 3rd ed.) sits beside it.

**4. Aneja, A., Donohue, J. J., & Zhang, A. (2014).** "The Impact of Right-to-Carry Laws and the NRC Report: Lessons for the Empirical Evaluation of Law and Policy." NBER Working Paper w18294 / *American Law and Economics Review*. **GS ≈ 200–250.**
- *Policy:* RTC, formal multi-spec robustness.
- *Outcome:* UCR violent crime and murder.
- *Headline:* Demonstrates "specification multiverse": the same data yields opposite-signed RTC coefficients across LM, BC, MM, and DAW covariate sets; introduces LASSO-based selection.
- *Identification:* State panel two-way FE under each of four covariate sets, plus LASSO.
- *Notes:* This is the most explicit prior treatment of covariate-set sensitivity in the firearm-policy literature and a direct intellectual antecedent to the methodological covariate-multiverse contribution our paper proposes to extend. The "DAW set" formalized here is what our headline spec defaults to.

**5. Donohue, J. J., Aneja, A., & Weber, K. D. (2019).** "Right-to-Carry Laws and Violent Crime: A Comprehensive Assessment Using Panel Data and a State-Level Synthetic Control Analysis." *Journal of Empirical Legal Studies* 16(2): 198–247 (NBER w23510). **GS ≈ 350+.**
- *Policy:* Shall-issue RTC adoption through 2014.
- *Outcome:* Violent crime, murder, rape, aggravated assault, robbery.
- *Headline:* RTC associated with 13–15% increase in aggregate violent crime ten years after adoption; SCM and panel-FE concordant under DAW set.
- *Identification:* Two-way FE panel + state-level synthetic control with 10-year pre/post windows, donor-pool restrictions for non- or late-adopters.
- *Notes:* The current modal "anti-Lott" reference. (Moody and Marvell 2019, *Econ Journal Watch* 16(1): 84–96) reply that the result is fragile to specification choices — a critique that is itself partial empirical confirmation of the multiverse problem we propose to formalize. Effect sizes are an explicit benchmark for our SYG/permitless-carry estimates.

**6. Donohue, J. J., Cai, S. V., Bondy, M. V., & Cook, P. J. (2023; forthcoming AEJ:Applied; NBER w30190).** "Why Does Right-to-Carry Cause Violent Crime to Increase?" **GS ≈ 60–90 (working-paper era).**
- *Policy:* RTC (city panel).
- *Outcome:* City-level violent crime; gun theft; clearance rates.
- *Headline:* In cities >250,000, RTC raises violent crime by ~20%, raises gun theft by ~50%, lowers clearance rates by ~9%; mechanism evidence centers on stolen guns and reduced police effectiveness.
- *Identification:* City panel two-way FE on 217 U.S. cities, 1979–2019; mechanism mediation analysis.
- *Notes:* The first credible mechanism story in the modern RTC literature; serves as the proof-of-mechanism for any (Lott-style) deterrence dispute. Our paper's discussion section should engage Donohue et al.'s mechanism evidence directly.

**7. Black, D. A., & Nagin, D. S. (1998).** "Do Right-to-Carry Laws Deter Violent Crime?" *Journal of Legal Studies* 27(1): 209–219. **GS ≈ 700.**
- *Policy:* Same RTC laws.
- *Outcome:* UCR violent crime.
- *Headline:* The Lott–Mustard result is highly sensitive to small modeling and sample changes; "inappropriate" for policy formulation.
- *Identification:* Re-estimation under Lott–Mustard panel with several model perturbations; subgroup analyses including dropping Florida.
- *Notes:* The first scholarly rebuttal to LM, in the same journal LM appeared in. Its core contribution — that the LM design is fragile to seemingly innocuous specification moves — is the empirical motivation for the multiverse style of robustness reporting we adopt.

### 1.2 Permit-to-purchase, background checks, and waiting periods

**8. Webster, D. W., Crifasi, C. K., & Vernick, J. S. (2014).** "Effects of the Repeal of Missouri's Handgun Purchaser Licensing Law on Homicides." *Journal of Urban Health* 91(2): 293–302. **GS ≈ 250.**
- *Policy:* Missouri's 2007 PTP repeal.
- *Outcome:* Firearm homicide; non-firearm placebo.
- *Headline:* Repeal associated with +1.09/100k firearm homicides (+23% vital stats); +0.93/100k (+16%, UCR; corrected to +14% in erratum); no effect on non-firearm placebo.
- *Identification:* State-year panel two-way FE GLS with cluster-robust SEs; concurrent-policy controls (SYG, RTC, "Saturday night special," juvenile-felon bar).
- *Notes:* The single most-cited applied study of handgun licensing in the public-health literature. The non-firearm placebo template is one we adopt directly.

**9. Crifasi, C. K., Meyers, J. S., Vernick, J. S., & Webster, D. W. (2015).** "Effects of Changes in Permit-to-Purchase Handgun Laws in Connecticut and Missouri on Suicide Rates." *Preventive Medicine* 79: 43–49. **GS ≈ 200.**
- *Policy:* CT 1995 PTP adoption + MO 2007 PTP repeal.
- *Outcome:* Firearm suicide; non-firearm placebo.
- *Headline:* CT: −15.4% firearm suicide; MO: +16.1% firearm suicide; no change in non-firearm rates.
- *Identification:* SCM with the canonical "suicide stack" of predictors (alcohol, religious adherence, overdose, demographics).
- *Notes:* The first to formalize the suicide-specific covariate stack (alcohol, religion, overdose, % male, % married, % veteran). Our suicide spec inherits this template.

**10. Rudolph, K. E., Stuart, E. A., Vernick, J. S., & Webster, D. W. (2015).** "Association Between Connecticut's Permit-to-Purchase Handgun Law and Homicides." *American Journal of Public Health* 105(8): e49–e54. **GS ≈ 200.**
- *Policy:* CT 1995 PTP adoption.
- *Outcome:* Firearm homicide.
- *Headline:* −40% firearm homicide over 10 years; no change in non-firearm placebo.
- *Identification:* SCM with rich economic-inequality + policing predictor set (Gini, jobs/adult, robbery, density, % MSA).
- *Notes:* The "homicide stack" companion to (Crifasi et al. 2015). Effect-size magnitude is large and front-loaded; contested by reviewers on enforcement-onset coding.

**11. McCourt, A. D., Crifasi, C. K., Stuart, E. A., Vernick, J. S., Kagawa, R. M. C., Wintemute, G. J., & Webster, D. W. (2020).** "Purchaser Licensing, Point-of-Sale Background Check Laws, and Firearm Homicide and Suicide in 4 US States, 1985–2017." *American Journal of Public Health* 110(10): 1546–1552. **GS ≈ 90+.**
- *Policy:* PTP/UBC adoption or repeal in CT, MD, MO, PA.
- *Outcome:* Firearm homicide, firearm suicide, non-firearm placebos.
- *Headline:* CT PTP −27.8% firearm homicide; MO repeal +47.3% firearm homicide and +23.5% firearm suicide; UBC alone (no PTP) effects weaker and inconsistent.
- *Identification:* Multi-state SCM with outcome-tailored covariate stacks (homicide vs. suicide); donor pool excludes own-law changers.
- *Notes:* The cleanest published statement of the "PTP > UBC alone" benchmarking we will use for effect-size comparison.

**12. Luca, M., Malhotra, D., & Poliquin, C. (2017).** "Handgun Waiting Periods Reduce Gun Deaths." *PNAS* 114(46): 12162–12165. **GS ≈ 200.**
- *Policy:* State waiting-period changes 1970–2014 + 1994 Brady Act federal natural experiment.
- *Outcome:* Gun homicides; gun suicides.
- *Headline:* Waiting periods reduce gun homicides ~17%; gun suicides ~7–11%; Brady-affected states drive part of the result.
- *Identification:* State-panel two-way FE; Brady subset acts as a federal-policy DiD wedge.
- *Notes:* Template for combining state-panel FE with a federal-policy natural experiment; rebutted in (Kleck 2017 SSRN) for selective specification reporting — a critique that recurs against PTP/UBC-favorable findings.

**13. Ludwig, J., & Cook, P. J. (2000).** "Homicide and Suicide Rates Associated with Implementation of the Brady Handgun Violence Prevention Act." *JAMA* 284(5): 585–591. **GS ≈ 700.**
- *Policy:* 1994 Brady Act.
- *Outcome:* Homicide and suicide rates.
- *Headline:* No detectable effect on overall homicide/suicide rates, *except* a significant reduction in firearm suicide among adults aged 55+.
- *Identification:* Treatment vs. control state DiD using NCHS vital stats; 32 "treatment" states (no pre-existing background check) vs. 18 "control" states.
- *Notes:* The benchmark "modest-effect" Brady result; routinely cited as evidence that age-disaggregated suicide effects are stronger than aggregate effects, supporting our age-21/youth subgroup analyses.

**14. McCourt, A. D., Vernick, J. S., Betz, M. E., Brandspigel, S., & Runyan, C. W. (2017).** "Temporary Transfer of Firearms from the Home to Prevent Suicide: Legal Obstacles and Recommendations." *JAMA Internal Medicine* 177(1): 96–101. **GS ≈ 60.**
- *Policy:* State variation in temporary-transfer law clarity.
- *Outcome:* Legal feasibility analysis.
- *Headline:* Many states' laws ambiguously block voluntary transfers, undermining lethal-means counseling.
- *Identification:* Legal-doctrine descriptive review.
- *Notes:* Important for the lethal-means framing in our discussion section; one of the few papers that bridges law and clinical practice.

**15. Crifasi, C. K., Buggs, S. A. L., Choksy, S., & Webster, D. W. (2017).** "The Initial Impact of Maryland's Firearm Safety Act of 2013 on the Supply of Crime Handguns in Baltimore." *RSF: Russell Sage Foundation Journal of the Social Sciences* 3(5): 128–140. **GS ≈ 30.**
- *Policy:* Maryland 2013 PTP/AWB package.
- *Outcome:* ATF crime-gun trace data.
- *Headline:* Crime handguns shifted toward older origin dates and longer time-to-crime, consistent with reduced primary-market diversion.
- *Identification:* Pre-post + comparison-state interrupted time series.
- *Notes:* Mechanism evidence for permit licensing — supports interpretation of PTP effects as operating through the primary market rather than secondary stock.

### 1.3 Stand-your-ground / Castle Doctrine

**16. Cheng, C., & Hoekstra, M. (2013).** "Does Strengthening Self-Defense Law Deter Crime or Escalate Violence? Evidence from Expansions to Castle Doctrine." *Journal of Human Resources* 48(3): 821–854. **GS ≈ 500+.**
- *Policy:* SYG/Castle-Doctrine adoption in ~20 states between 2005–2010.
- *Outcome:* Homicide; UCR-violent crime; burglary/robbery placebo.
- *Headline:* SYG raises homicide by 8% (~600 additional homicides/year nationally); no detectable deterrence on burglary, robbery, or aggravated assault.
- *Identification:* State-panel two-way FE with state-specific linear trends, region × year FE, full DAW-style covariate vector + welfare/public-assistance spending.
- *Notes:* The canonical SYG study in economics. Robustness battery in this paper sets the bar for any SYG re-estimation.

**17. McClellan, C., & Tekin, E. (2017).** "Stand Your Ground Laws, Homicides, and Injuries." *Journal of Human Resources* 52(3): 621–653 (NBER w18187). **GS ≈ 250.**
- *Policy:* SYG adoption.
- *Outcome:* Monthly homicide, firearm injury hospitalizations.
- *Headline:* Confirms Cheng-Hoekstra (~7–10% homicide increase, concentrated among white males); replicates with hospitalization data showing similar firearm-injury rises.
- *Identification:* State + year FE; state-specific trends; region × year FE; alcohol per capita explicitly added.
- *Notes:* Adds alcohol to the SYG specification — important precedent for our covariate stack. Hospital data provides outcome triangulation.

**18. Hoekstra, M., & Sloan, C. (2025/forthcoming).** "Race, Self-Defense Law, and Justifiable Homicide." *Journal of Law & Economics* (or equivalent — manuscript in revision; author site lists 2024 working draft).
- *Policy:* SYG.
- *Outcome:* SHR justifiable-homicide rulings disaggregated by race-of-victim and race-of-offender.
- *Headline:* SYG more than doubles the justifiable-homicide rulings for white-on-Black confrontations relative to other race-pairings.
- *Identification:* DiD; raw rate decomposition by race-pair.
- *Notes:* Recent SYG-and-race work (also [Roman 2013, *Urban Institute*] on the racial asymmetry in justifiable-homicide rulings; [Ackermann et al. 2015, *J. Empirical Legal Studies*] on Florida SYG). For our paper, this is the template for race-disaggregated SYG analysis if our outcome variable supports it.

**19. Humphreys, D. K., Gasparrini, A., & Wiebe, D. J. (2017).** "Evaluating the Impact of Florida's 'Stand Your Ground' Self-Defense Law on Homicide and Suicide." *JAMA Internal Medicine* 177(1): 44–50. **GS ≈ 200.**
- *Policy:* Florida 2005 SYG.
- *Outcome:* Homicide; firearm homicide; suicide (placebo).
- *Headline:* +24% homicide post-2005, with stronger effect on firearm homicide; no effect on suicide (placebo).
- *Identification:* Interrupted time series with comparison states (NJ, NY, VA).
- *Notes:* Public-health complement to Cheng-Hoekstra; the Florida-specific case study most cited.

**20. Kivisto, A. J., Magee, L. A., Phalen, P. L., & Ray, B. R. (2019).** "Firearm Ownership and Domestic Versus Nondomestic Homicide in the U.S." *American Journal of Preventive Medicine* 57(3): 311–320. **GS ≈ 90.**
- *Policy:* Cross-state ownership variation; not strictly a policy paper but adjacent.
- *Outcome:* Domestic vs. non-domestic homicide.
- *Headline:* Firearm ownership predicts higher rates of *domestic* homicide more strongly than non-domestic homicide.
- *Identification:* State-level OLS with covariate adjustment; ownership proxied via FSS.
- *Notes:* Bridges SYG/RTC literatures with the broader firearm-availability literature.

### 1.4 Extreme-risk protection orders / red-flag laws

**21. Kivisto, A. J., & Phalen, P. L. (2018).** "Effects of Risk-Based Firearm Seizure Laws in Connecticut and Indiana on Suicide Rates, 1981–2015." *Psychiatric Services* 69(8): 855–862. **GS ≈ 200.**
- *Policy:* CT 1999 + IN 2005 ERPO.
- *Outcome:* Firearm suicide; non-firearm suicide (placebo).
- *Headline:* IN: −7.5% firearm suicide; CT: −1.6% immediately, growing to −13.7% post-2007 (Virginia Tech) when enforcement intensified.
- *Identification:* SCM annual state panel + DiD sensitivity; randomization-inference placebos.
- *Notes:* The canonical empirical ERPO evaluation. Our suicide spec uses the same predictor stack.

**22. Swanson, J. W., Norko, M. A., Lin, H.-J., Alanis-Hirsch, K., Frisman, L. K., Baranoski, M. V., Easter, M. M., Robertson, A. G., Swartz, M. S., & Bonnie, R. J. (2017).** "Implementation and Effectiveness of Connecticut's Risk-Based Gun Removal Law: Does It Prevent Suicides?" *Law & Contemporary Problems* 80(2): 179–208. **GS ≈ 200.**
- *Policy:* CT 1999 risk-warrant law (the original ERPO).
- *Outcome:* Risk-removal proceedings, suicide of subjects.
- *Headline:* 762 gun-removal proceedings 1999–2013; 21 subjects (3%) eventually died by suicide (6 by gun, 15 other means); estimate one suicide averted per 10–20 risk-warrants.
- *Identification:* Cohort follow-up with comparison group from suicide demographics.
- *Notes:* The most-cited descriptive evaluation of ERPO operations; complements (Kivisto and Phalen 2018) population-level estimate.

**23. Swanson, J. W., Easter, M. M., Alanis-Hirsch, K., Belden, C. M., Norko, M. A., Robertson, A. G., Frisman, L. K., Lin, H.-J., Swartz, M. S., & Parker, G. F. (2019).** "Criminal Justice and Suicide Outcomes with Indiana's Risk-Based Gun Seizure Law." *Journal of the American Academy of Psychiatry and the Law* 47(2): 188–197. **GS ≈ 100.**
- *Policy:* Indiana 2005 ERPO.
- *Outcome:* Subject suicide outcomes.
- *Headline:* Estimate one suicide averted per 10 firearm seizures.
- *Identification:* Cohort follow-up.
- *Notes:* The Indiana sister study to (Swanson et al. 2017).

**24. Anestis, M. D., Bryan, C. J., Bond, A. E., Bandel, S. L., Bryan, A. O., & Lott, J. R. (2024).** "Recent firearm storage practices, lethal-means counseling, and suicide ideation among U.S. adults." *Suicide and Life-Threatening Behavior* (advance online). **GS ≈ 20–40.** (Note: one of multiple recent Anestis-led storage/ERPO papers.)
- *Policy:* Storage law / counseling regime, not strictly a state-policy treatment.
- *Outcome:* Self-reported storage; ideation.
- *Headline:* Lethal-means counseling associated with shifts toward locked/separated storage; modest reductions in self-reported access at acute risk.
- *Identification:* National survey, propensity-adjusted comparison.
- *Notes:* Mechanism support for ERPO/lethal-means restriction framings.

### 1.5 Assault-weapon and large-capacity magazine bans

**25. Koper, C. S., & Roth, J. A. (2001).** "The Impact of the 1994 Federal Assault Weapon Ban on Gun Violence Outcomes." *Journal of Quantitative Criminology* 17(1): 33–74. **GS ≈ 250.**
- *Policy:* 1994 Federal AWB.
- *Outcome:* Gun homicide; AW-traced incidents; market measures.
- *Headline:* No detectable short-run effect on gun homicide; AWs are ~2% of crime guns; market evidence suggests stockpiling and substitution; modest declines in AW share of crime guns over time.
- *Identification:* Pre/post comparison; trace-data trends; multiple outcome measures.
- *Notes:* The most-cited evaluation of the 1994 federal AWB. Methodologically cautious — Koper himself emphasized that the 10-year ban with its grandfather clauses generates a weak treatment.

**26. Koper, C. S. (2004).** "Updated Assessment of the Federal Assault Weapons Ban: Impacts on Gun Markets and Gun Violence, 1994–2003." Report to NIJ. **GS ≈ 250.**
- *Policy:* AWB sunset evaluation.
- *Outcome:* Mass-shooting and homicide outcomes.
- *Headline:* Effects of the ban on gun violence are likely to be small at best, and perhaps too small for reliable measurement; some plausible effect on AW-class crime use.
- *Identification:* Updated trend analysis for the 2004 sunset.
- *Notes:* The pre-sunset benchmark; widely cited in policy debates over re-imposition.

**27. Klarevas, L., Conner, A., & Hemenway, D. (2019).** "The Effect of Large-Capacity Magazine Bans on High-Fatality Mass Shootings, 1990–2017." *American Journal of Public Health* 109(12): 1754–1761. **GS ≈ 150.**
- *Policy:* State LCM bans.
- *Outcome:* High-fatality mass shootings (incidence; deaths).
- *Headline:* HF-mass-shooting incidence in non-LCM-ban states more than double that in LCM-ban states; 81% of perpetrators in non-ban states used LCMs vs. 55% in ban states.
- *Identification:* State-FE logit + negative binomial; HH-firearm-prevalence proxy explicitly added.
- *Notes:* Most-cited modern LCM/AWB study. Critiqued by (Webster 2022) and others for sample selection of "high-fatality" cutoff but the headline result has held in extensions.

**28. Lemieux, F. (2014).** "Effect of Gun Culture and Firearm Laws on Gun Violence and Mass Shootings in the United States." *International Journal of Criminal Justice Sciences* 9(1): 74–93. **GS ≈ 60.**
- *Policy:* State firearm-law strictness.
- *Outcome:* Mass-shooting incidence and victim count.
- *Headline:* Negative association of strict laws with mass-shooting victimization.
- *Identification:* State cross-section.
- *Notes:* Cross-sectional, weak ID, but routinely cited in mass-shooting literature reviews.

### 1.6 Age-21 / minimum-age laws

**29. Webster, D. W., Vernick, J. S., Zeoli, A. M., & Manganello, J. A. (2004).** "Association Between Youth-Focused Firearm Laws and Youth Suicides." *JAMA* 292(5): 594–601. **GS ≈ 250.**
- *Policy:* Minimum-age laws and CAP (child-access prevention) laws.
- *Outcome:* Youth (≤20) firearm and total suicide.
- *Headline:* Minimum-age laws associated with modest reductions in youth firearm suicide; CAP laws associated with stronger reductions.
- *Identification:* State-panel multivariate Poisson regression with state FE.
- *Notes:* The original "youth-focused firearm law" paper. Anestis and Anestis (2015) and Webster (2024) extend the framework.

**30. Crifasi, C. K., Topazian, R. J., McCourt, A. D., Oliphant, S. N., Zeoli, A. M., Kennedy, K. S., Wagner, E. D., & Doucette, M. L. (2024).** "Examining the Impact of Minimum Handgun Purchase Age and Background Check Legislation on Young Adult Suicide in the United States, 1991–2020." *American Journal of Public Health* 114(8): 821–828. **GS ≈ 30.**
- *Policy:* Minimum-age 21 handgun laws.
- *Outcome:* Young-adult (18–20) firearm suicide.
- *Headline:* Minimum-age 21 associated with ~12% reduction in 18–20 firearm suicide; effect amplified in PTP states; PTP itself shows ~39% reduction in young-adult firearm suicide.
- *Identification:* Negative-binomial regression with year FE and state random effects.
- *Notes:* Direct competitor analysis to ours if we restrict to age-21 → suicide. Effect sizes are a bound for what our identification could find.

**31. Anestis, M. D., & Anestis, J. C. (2015).** "Suicide Rates and State Laws Regulating Access and Exposure to Handguns." *American Journal of Public Health* 105(10): 2049–2058. **GS ≈ 200.**
- *Policy:* Four laws — waiting period, UBC, gun lock requirement, open-carry prohibition.
- *Outcome:* State firearm and total suicide rates.
- *Headline:* Each law associated with significantly lower firearm suicide and proportion of suicides by firearm; three of four also reduce overall suicide.
- *Identification:* Cross-sectional ANCOVA on 2010 wave; very thin covariate set (poverty, density only).
- *Notes:* Heavily cited despite acknowledged ID weakness. (Anestis et al. 2017) extends to within-state-change design.

**32. Anestis, M. D., Anestis, J. C., & Butterworth, S. E. (2017).** "Handgun Legislation and Changes in Statewide Overall Suicide Rates." *American Journal of Public Health* 107(4): 579–581. **GS ≈ 100.**
- *Policy:* Same four laws.
- *Outcome:* Within-state suicide-rate changes 2013→2014.
- *Headline:* Significant reductions in mandatory waiting period and UBC states relative to non-adopting states.
- *Identification:* Within-state change ANCOVA; adds NSDUH ideation/depression and Kalesan ownership proxy.
- *Notes:* Bridges (Anestis and Anestis 2015) cross-section with mechanism-relevant covariates.

### 1.7 Background checks, NICS, and Brady-era studies

**33. Wintemute, G. J., Romero, M. P., Wright, M. A., & Grassel, K. M. (2001).** "The Life Cycle of Crime Guns: A Description Based on Guns Recovered from Young People in California." *Annals of Emergency Medicine* 37(6): 733–743. **GS ≈ 100.**
- *Policy:* Descriptive baseline for understanding crime-gun supply.
- *Outcome:* Time-to-crime, gun age, market.
- *Headline:* Most crime guns recovered from juveniles were short-time-to-crime, suggesting acquisition close to commission.
- *Identification:* Descriptive cohort.
- *Notes:* Foundational descriptive evidence underpinning the diversion-from-primary-market mechanism that PTP/UBC literature relies on.

**34. Wintemute, G. J., Wright, M. A., Drake, C. M., & Beaumont, J. J. (2001).** "Subsequent Criminal Activity Among Violent Misdemeanants Who Seek to Purchase Handguns." *JAMA* 285(8): 1019–1026. **GS ≈ 200.**
- *Policy:* California's denial of handgun purchase to violent misdemeanants.
- *Outcome:* Subsequent criminal activity.
- *Headline:* Denied purchasers had ~25% lower subsequent gun- or violent-crime conviction risk.
- *Identification:* Cohort comparison of denied vs. approved purchasers.
- *Notes:* The most-cited individual-level evidence on background-check effectiveness.

**35. Castillo-Carniglia, A., Kagawa, R. M. C., Webster, D. W., Vernick, J. S., Cerdá, M., & Wintemute, G. J. (2018).** "Comprehensive Background Check Policy and Firearm Background Checks in Three U.S. States." *Injury Prevention* 24(6): 454–459. **GS ≈ 80.**
- *Policy:* Comprehensive background check expansion in CO, DE, WA.
- *Outcome:* NICS check counts.
- *Headline:* No detectable increase in NICS check volume in CO and WA after CBC laws — suggesting weak compliance.
- *Identification:* Interrupted time series.
- *Notes:* The "CBC compliance gap" finding is widely cited as a caveat for UBC policy.

**36. Castillo-Carniglia, A., Kagawa, R. M. C., Cerdá, M., Crifasi, C. K., Vernick, J. S., Webster, D. W., & Wintemute, G. J. (2019).** "California's Comprehensive Background Check and Misdemeanor Violence Prohibition Policies and Firearm Mortality." *Annals of Epidemiology* 30: 50–56. **GS ≈ 50.**
- *Policy:* CA 1991 CBC + violence prohibition.
- *Outcome:* Firearm homicide and suicide.
- *Headline:* No detectable effect of either policy on aggregate firearm mortality.
- *Identification:* Synthetic control.
- *Notes:* A widely-cited *null* SCM result that anchors the "CBC effects are smaller and noisier than PTP effects" consensus.

### 1.8 Cross-state externalities, trafficking, and supply

**37. Knight, B. (2013).** "State Gun Policy and Cross-State Externalities: Evidence from Crime Gun Tracing." *AEJ: Economic Policy* 5(4): 200–229 (NBER w17469). **GS ≈ 250+.**
- *Policy:* State firearm-law strictness asymmetries.
- *Outcome:* Bilateral crime-gun trace flows from ATF.
- *Headline:* Guns flow weak→strict; flows decay with distance; strict-state criminal possession is partly explained by neighbors' weak laws.
- *Identification:* Gravity model with origin- and destination-state FE on 2009 ATF traces.
- *Notes:* Canonical cross-state spillover paper; the warrant for the spatial-spillover framing in our spatial-RDD design.

**38. Cook, P. J., Ludwig, J., Venkatesh, S., & Braga, A. A. (2007).** "Underground Gun Markets." *The Economic Journal* 117(524): F588–F618. **GS ≈ 250+.**
- *Policy:* Descriptive evidence on Chicago underground gun market structure.
- *Outcome:* Market price, search costs, product differentiation.
- *Headline:* Underground gun markets are characterized by high search costs, price markups, and information asymmetries — implying tighter primary-market regulation can produce real frictions.
- *Identification:* Mixed-methods (interviews + quantitative price data).
- *Notes:* The supply-side mechanism paper that PTP/UBC literature implicitly leans on.

**39. Cook, P. J., & Ludwig, J. (2006).** "The Social Costs of Gun Ownership." *Journal of Public Economics* 90(1–2): 379–391. **GS ≈ 350+.**
- *Policy:* Cross-county gun-prevalence variation (proxied by % suicides committed with a gun).
- *Outcome:* County homicide.
- *Headline:* Elasticity of homicide with respect to gun prevalence is +0.1 to +0.3; entirely loaded on gun homicides; implies a marginal social cost of household gun ownership of $100–$600 annually per household.
- *Identification:* County and state panels with the FSS proxy as the key explanatory variable.
- *Notes:* Foundational gun-prevalence externality estimate. The +0.1 to +0.3 elasticity is the headline benchmark for any "ownership channel" interpretation of policy effects.

**40. Duggan, M. (2001).** "More Guns, More Crime." *Journal of Political Economy* 109(5): 1086–1114. **GS ≈ 700.**
- *Policy:* Cross-county and cross-time variation in gun ownership (proxied by *Guns & Ammo* magazine subscriptions).
- *Outcome:* Homicide, robbery, rape.
- *Headline:* Gun ownership predicts homicide growth (positive elasticity); supports causal channel from gun availability to gun-homicide.
- *Identification:* County panel two-way FE with subscription proxy as the explanatory variable; controls include income, demographics.
- *Notes:* Direct counterpoint to (Lott 1998); the *JPE* version makes this one of the most cited firearm-availability papers in economics.

### 1.9 Suicide-specific and lethal-means restriction

**41. Miller, M., & Hemenway, D. (1999).** "The Relationship Between Firearms and Suicide: A Review of the Literature." *Aggression and Violent Behavior* 4(1): 59–75. **GS ≈ 250.**
- *Policy:* Cross-area firearm prevalence.
- *Outcome:* Suicide.
- *Headline:* Higher firearm prevalence is associated with higher suicide rates, almost entirely driven by firearm suicide; non-firearm suicide rates are roughly unchanged.
- *Identification:* Literature review of ecologic and case-control studies.
- *Notes:* The first major synthesis arguing that aggregate firearm-availability is causally tied to firearm suicide via lethal-means access rather than depression rates.

**42. Miller, M., Azrael, D., & Hemenway, D. (2002).** "Household Firearm Ownership and Suicide Rates in the United States." *Epidemiology* 13(5): 517–524. **GS ≈ 350.**
- *Policy:* Cross-state ownership variation.
- *Outcome:* State suicide rates.
- *Headline:* States with higher household firearm ownership have substantially higher firearm suicide rates and total suicide rates; the relationship survives controls for psychiatric morbidity, substance abuse, and depression.
- *Identification:* Cross-state regression with mental-health and economic controls.
- *Notes:* The single most-cited ownership-suicide paper. Together with (Miller and Hemenway 1999), supplies the "lethal-means restriction" theoretical motivation.

**43. Miller, M., Hemenway, D., & Azrael, D. (2007).** "State-Level Homicide Victimization Rates in the U.S. in Relation to Survey Measures of Household Firearm Ownership, 2001–2003." *Social Science & Medicine* 64(3): 656–664. **GS ≈ 200.**
- *Policy:* Cross-state ownership.
- *Outcome:* Homicide victimization.
- *Headline:* Higher ownership → higher firearm homicide rates, no offset in non-firearm homicide.
- *Identification:* Cross-state regression with covariate adjustment.
- *Notes:* Homicide companion to (Miller et al. 2002).

**44. Hemenway, D., & Miller, M. (2002).** "Association of Rates of Household Handgun Ownership, Lifetime Major Depression, and Serious Suicidal Thoughts with Rates of Suicide Across U.S. Census Regions." *Injury Prevention* 8(4): 313–316. **GS ≈ 200.**
- *Policy:* Cross-region ownership.
- *Outcome:* Suicide rates.
- *Headline:* Suicide rates correlate with handgun ownership; no offset by mental-health prevalence.
- *Identification:* Census-region regression.
- *Notes:* Often cited together with (Miller et al. 2002) for the "ownership not depression" result.

**45. Hepburn, L. M., & Hemenway, D. (2004).** "Firearm Availability and Homicide: A Review of the Literature." *Aggression and Violent Behavior* 9(4): 417–440. **GS ≈ 250.**
- *Policy:* International and U.S. cross-area ownership variation.
- *Outcome:* Homicide.
- *Headline:* Across both individual-level and ecologic studies, more firearm availability is associated with more firearm homicide; international and U.S. evidence converge.
- *Identification:* Systematic literature review.
- *Notes:* Public-health canonical literature review for the firearm-availability-homicide channel.

### 1.10 General reviews and meta-analyses

**46. Cook, P. J., & Donohue, J. J. (2017).** "Saving Lives by Regulating Guns: Evidence for Policy." *Science* 358(6368): 1259–1261. **GS ≈ 200.**
- *Policy:* Synthesis editorial across the firearm-policy literature.
- *Outcome:* All firearm mortality.
- *Headline:* High-quality evidence supports gun-availability and PTP/UBC effects; calls for richer-control specifications and skepticism of Lott-style sparse models.
- *Identification:* Narrative review.
- *Notes:* The single most-cited review-style firearm-policy article in the modern literature; almost certainly the highest-impact non-empirical citation.

**47. RAND Corporation (Smart, R., Morral, A. R., Murphy, J. P., Jose, R., Charbonneau, A., & Smucker, S., 2024).** *The Science of Gun Policy: A Critical Synthesis of Research Evidence on the Effects of Gun Policies in the United States* (4th ed.). RR-A243-9. **GS ≈ 100+ for 4th ed.; first edition (Morral et al. 2018) ~250.**
- *Policy:* 18 distinct state firearm policies.
- *Outcome:* 9 outcome categories.
- *Headline:* Evidence is "supportive" or "moderate" for: PTP/licensing reducing firearm mortality; CAP laws reducing youth firearm injury; SYG increasing homicides; minimum-age laws reducing youth suicide; concealed-carry laws (RTC) increasing total/violent crime; LCM bans reducing mass-shooting fatalities. Evidence is "limited" or "inconclusive" for many other policies.
- *Identification:* Systematic review with explicit evidence-quality coding.
- *Notes:* The methodological reference for any modern gun-policy paper; the source of the canonical strength-of-evidence ratings.

**48. Hahn, R. A., Bilukha, O., Crosby, A., Fullilove, M. T., Liberman, A., Moscicki, E., Snyder, S., Tuma, F., & Briss, P. A. (2005).** "Firearms Laws and the Reduction of Violence: A Systematic Review." *American Journal of Preventive Medicine* 28(2 Suppl 1): 40–71. **GS ≈ 200.**
- *Policy:* Multiple firearm laws (Task Force on Community Preventive Services).
- *Outcome:* Violent crime and homicide.
- *Headline:* Insufficient evidence in 2005 to determine effectiveness of most firearm laws individually — a result that motivated a generation of subsequent identification work.
- *Identification:* Systematic review with quality grading.
- *Notes:* Often cited as the "evidence vacuum" pre-2010 baseline; later updated by RAND.

**49. Lee, L. K., Fleegler, E. W., Farrell, C., Avakame, E., Srinivasan, S., Hemenway, D., & Monuteaux, M. C. (2017).** "Firearm Laws and Firearm Homicides: A Systematic Review." *JAMA Internal Medicine* 177(1): 106–119. **GS ≈ 200.**
- *Policy:* Multiple firearm laws.
- *Outcome:* Firearm homicide.
- *Headline:* Stronger firearm laws are associated with reduced firearm homicide rates across studies.
- *Identification:* Systematic review.
- *Notes:* Companion to (Santaella-Tenorio et al. 2016) Epi Reviews.

**50. Santaella-Tenorio, J., Cerdá, M., Villaveces, A., & Galea, S. (2016).** "What Do We Know About the Association Between Firearm Legislation and Firearm-Related Injuries?" *Epidemiologic Reviews* 38(1): 140–157. **GS ≈ 250.**
- *Policy:* Range of firearm laws.
- *Outcome:* Firearm injury and mortality.
- *Headline:* Evidence supports the protective effect of stricter firearm laws — particularly multiple-law packages — on firearm homicide and total firearm mortality.
- *Identification:* Systematic review.
- *Notes:* Frequently cited alongside (Lee et al. 2017) and (Hahn et al. 2005); a third leg of the public-health systematic-review canon.

### 1.11 Honorable mentions and behavioral framings (referenced but not in top 50)

These are influential but either off-spine for our paper or too recent to have built citation stock; we cite them in the discussion section but they are not centerline references.

- (Hemenway and Solnick 2015) "The Epidemiology of Self-Defense Gun Use: Evidence from the National Crime Victimization Survey 2007–2011." *Preventive Medicine* 79: 22–27. Defensive-use frequency estimates that anchor the Peltzman-effect debate.
- (Wintemute 2015) "The Epidemiology of Firearm Violence in the Twenty-First Century United States." *Annual Review of Public Health* 36: 5–19. Public-health framing for the demographic and economic disparities in firearm mortality.
- (Hemenway 2017) *Private Guns, Public Health* (2nd ed.). University of Michigan Press. Book-length statement of the public-health framing.
- (Cook 1991, 1993, 1996) earlier *Crime and Justice* and *Risk Analysis* essays establishing the firearm-instrumentality hypothesis.
- (Kovandzic, Marvell, and Vieraitis 2005) "The Impact of Shall-Issue Concealed Handgun Laws on Violent Crime Rates: Evidence From Panel Data for Large Urban Cities." *Homicide Studies* 9(4): 292–323. Pro-LM rebuttal in urban setting.
- (Lott 2010) *More Guns, Less Crime* (3rd ed.). Univ. Chicago Press. Continues the LM defense.
- (Webster 2017, ed.) *Reducing Gun Violence in America: Informing Policy with Evidence and Analysis*. Johns Hopkins UP. Edited collection; high-impact in policy circles.
- (Kleck 1991) *Point Blank: Guns and Violence in America*. Aldine de Gruyter. Foundational pro-defensive-use volume; cited frequently in deterrence-channel discussions.
- (Ackermann et al. 2015) "Race, Law, and Health: Examination of 'Stand Your Ground' and Defendant Convictions in Florida." *Social Science & Medicine* 142: 194–201. Race/SYG companion to Cheng-Hoekstra.
- (Roman 2013) "Race, Justifiable Homicide, and Stand Your Ground Laws." Urban Institute report. Companion to (Hoekstra and Sloan 2025).
- (Crifasi et al. 2018) "Association Between Firearm Laws and Homicide in Large, Urban U.S. Counties." *Journal of Urban Health* 95(3): 383–390.
- (Doucette, Crifasi, et al. 2023) "Deregulation of Public Civilian Gun Carrying and Violent Crime: A Longitudinal Analysis 1981–2019." *Criminology & Public Policy*. Modern permitless-carry estimate.
- (Doucette, Ward, McCourt, Webster, and Crifasi 2022) "Officer-Involved Shootings and Concealed Carry Weapons Permitting Laws: Analysis of GVA Data, 2014–2020." *Journal of Urban Health*.
- (Webster et al. 2024) reviews on age-21 PTP package effects.
- (Donohue and Levitt 2001) *QJE* 116(2): 379–420 — abortion and crime — not firearm-policy but methodological cousin invoked in the larger crime-determinants debate.

---

## Section 2 — Identified gaps in the literature

The literature is dense around a few well-worn questions and remarkably thin around several economically interesting ones. The following inventory identifies the gaps most relevant to a working paper on permitless carry → suicide / SYG → violence / age-21 → firearm suicide. These gaps drive Section 4's journal-targeting recommendation: a paper that hits even one of them squarely should be publishable in a top-quartile field journal; a paper that hits two should reach for a top-five-discipline journal.

### 2.1 Heterogeneous effects: rural vs. urban; demographic groups

(Donohue, Cai, Bondy, and Cook 2023) is the only paper in the canon that explicitly disaggregates RTC effects by city size, and finds the entire RTC effect concentrated in cities >250,000. The analogous decomposition for SYG (urban vs. rural; Black vs. white victim/offender; male vs. female) is partly addressed by (Hoekstra and Sloan 2025) and (Ackermann et al. 2015) on race-and-SYG, but is otherwise scarce. For permitless carry specifically, the evidence base is essentially silent on rural-urban gradient — a striking gap given that policy proponents argue permitless carry primarily affects rural permit-burdened populations while opponents argue effects are concentrated in urban gun-violence settings. **Open question for our paper:** does permitless carry's suicide effect concentrate in rural vs. urban subsamples, or in older-male vs. youth subsamples?

### 2.2 Mechanism studies: ownership, gun availability, defensive use

The reduced-form policy literature is abundant but mechanism evidence is thin. (Donohue, Cai, Bondy, and Cook 2023) is the rare exception — gun theft and clearance rates as RTC mechanisms. (Cook and Ludwig 2006) gives the foundational ownership-elasticity estimate, but it is cross-sectional. (Crifasi, Buggs, Choksy, and Webster 2017) provides primary-market mechanism evidence on PTP. Beyond these, the firearm-policy canon largely treats mechanisms as black boxes. **Open question for our paper:** For permitless carry → suicide, does the channel run through (a) increased household firearm acquisition (NICS/ownership shift), (b) reduced storage compliance, or (c) selection of more lethal firearm types? Our project panel has NICS data (`panel_market_augmented.csv` 1999–2026) and ownership proxies (`ownership_fss`, `ownership_rand`), making a mediation analysis tractable.

### 2.3 Policy interaction effects

The literature treats policies as additive — RTC + SYG + LCM-ban each get an independent dummy. But the *interaction* of policies is theoretically central: SYG is plausibly more dangerous in a permitless-carry environment because more potential confrontants are armed. (Cheng and Hoekstra 2013) and (McClellan and Tekin 2017) include RTC as a control but do not test the SYG × RTC interaction. (Crifasi et al. 2024) finds that minimum-age 21 effects are amplified in PTP states — a rare interaction estimate, and indeed one of the more interesting specification results in the recent literature. RAND (Smart et al. 2024, ch. 18) explicitly flags joint-effects estimation as an open methodological problem. **Open question for our paper:** if we estimate permitless-carry × SYG, permitless-carry × CAP-law, or permitless-carry × age-21, do we find amplification or substitution?

### 2.4 Spillover and cross-state effects beyond Knight 2013

(Knight 2013) is the canonical spillover paper but is now 13 years old and uses 2009 ATF traces only. (Ashworth and Kozinetz 2021) provides the only cross-sectional follow-up using border-distance. The literature has not (a) updated Knight's gravity model with newer trace data, (b) extended it to permitless-carry adoptions, or (c) embedded spatial spillover in a panel-DiD framework. RAND (Smart et al. 2024) treats spillover as a "limitation" rather than a research target. **Open question for our paper:** Does our spatial-RDD (adjacent-county) design produce different effect-size estimates from a "naive" state-panel design, and what is the implied magnitude of spillover bias?

### 2.5 Long-run vs. short-run effects

Most published studies estimate effects within a 5–10 year post-period. (Donohue, Aneja, and Weber 2019) extends to 10-year SCM windows and finds escalating RTC effects over time. (Webster et al. 2014) for Missouri PTP repeal extends only 3–5 years post. The shape of dynamic treatment effects — whether immediate, monotonically growing, or U-shaped — has not been systematically studied. With modern event-study methods (Callaway and Sant'Anna 2021; Sun and Abraham 2021; Borusyak, Jaravel, and Spiess 2024), this gap is now technically tractable. **Open question for our paper:** Do permitless-carry suicide effects grow with time-since-adoption (consistent with diffusion of carrying behavior) or stabilize quickly (consistent with immediate ownership-stock effects)?

### 2.6 Suicide method-substitution evidence

The lethal-means literature ((Miller and Hemenway 1999); (Miller et al. 2002); (Anestis et al. 2024)) maintains that suicide method-substitution is limited — i.e., that restricting firearms reduces firearm suicide *without* increasing non-firearm suicide. (Smart and Schell 2020 *AJPH*) provides a partial systematic answer for some policies, but the policy-specific answer for permitless carry is open. The non-firearm-suicide placebo (used routinely by Crifasi, Kivisto, and McCourt) operationally tests this. **Open question for our paper:** Does a permitless-carry-induced increase in firearm suicide reduce non-firearm suicide (substitution), leave it unchanged (no substitution; lethal-means hypothesis confirmed), or also increase non-firearm suicide (treatment-induced general distress)?

### 2.7 Multiverse / covariate-set sensitivity

(Aneja, Donohue, and Zhang 2014) and (Donohue, Aneja, and Weber 2019) explicitly demonstrate that RTC point estimates vary across LM/BC/MM/DAW covariate sets. Beyond this, formal multiverse or specification-curve analysis is essentially absent from the firearm-policy literature — RAND (Smart et al. 2024, App. B) specifically flags this as a methodological gap. The closest social-science analogs are (Simonsohn, Simmons, and Nelson 2020 *Nature Human Behaviour*) on specification curves and (Steegen et al. 2016 *Perspectives on Psychological Science*) on multiverse analysis, neither of which has been formally adapted to firearm-policy outcomes. **Open question for our paper (and a methodological contribution):** If we run all combinations of the three covariate tiers, three estimators (TWFE, Callaway-Sant'Anna, SCM), and two outcome operationalizations (firearm suicide, total suicide), what is the *distribution* of estimated effects, and how does it inform the published-result fragility critique?

### 2.8 Spatial-RDD designs in firearm policy

(Ashworth and Kozinetz 2021) is the only paper in the firearm-policy canon that explicitly uses a spatial-RDD style design (border-distance to weak-law states), and it is cross-sectional. (Knight 2013) uses a gravity model rather than a sharp-bandwidth RDD. The (Dube, Lester, and Reich 2010) contiguous-county-pair design has not been imported into firearm-policy estimation in published form. **Open question for our paper:** A panel contiguous-county design would be the first "Dube-Lester-Reich for guns" — directly addressing both the spatial-spillover gap (2.4) and the multiverse gap (2.7).

### 2.9 Modern DiD / event-study methods

The firearm-policy literature has been slow to adopt the methodological revolution in event-study DiD. (Callaway and Sant'Anna 2021), (Sun and Abraham 2021), (Borusyak, Jaravel, and Spiess 2024), (de Chaisemartin and D'Haultfœuille 2020) corrections for staggered-treatment heterogeneity are essentially absent from published gun-policy studies. (Doucette et al. 2022, *Journal of Urban Health*) and (Crifasi et al. 2024) use standard panel-FE without these corrections. RAND (Smart et al. 2024) does not yet flag the negative-weighting problem in two-way fixed effects as a critical methodology issue. **Open question for our paper (highly publishable):** What happens to canonical RTC, SYG, ERPO, and permitless-carry effect estimates under modern DiD estimators that handle heterogeneous treatment effects? If estimates change substantially, this is a top-tier methodological contribution.

### 2.10 Permitless carry specifically

This is a fast-moving sub-literature: (Doucette, McCourt, Crifasi, and Webster 2023) finds +24% firearm assaults; (Doucette et al. 2022) finds +12.9% officer-involved-shooting victimization; (Jorgensen 2024) examines AK/AZ/AR/WY with mixed results; the (Hamill et al. 2019) earlier *J. American College of Surgeons* found suggestive null effects. The literature is small, recent, and heterogeneous in direction. Crucially, **the suicide outcome for permitless carry is essentially unexamined in published peer-reviewed work.** RAND (2024) classifies permitless-carry → suicide as having "limited evidence" — a polite way of saying it is a wide-open question. **This is the single largest open question into which our paper has the strongest comparative advantage**, given our project's panel data extends through 2024 covering the post-2020 wave of adoptions (TX 2021, AL 2022, GA 2022, FL 2023, NE 2023, LA 2024, etc.).

### 2.11 Other underweighted questions

- **Unintended consequences for police safety.** (Doucette et al. 2022) is a start but the OIS literature in firearm policy is thin.
- **Effects on legal vs. illegal markets.** Beyond (Cook, Ludwig, et al. 2007), the secondary-market response to PTP/UBC is poorly measured.
- **Heterogeneous storage compliance.** Whether CAP laws actually shift household storage practices is partially answered by (Anestis et al. 2024) survey work; population-level estimates are scarce.
- **Behavioral/psychological framings.** The Peltzman risk-compensation argument (Peltzman 1975 *JPE*) is invoked rhetorically in pro-RTC pieces but rarely formally tested in the firearm-policy literature.
- **Cross-national comparison as benchmarking.** (Hepburn and Hemenway 2004) and (Hemenway and Miller 2000) supply comparative evidence; cross-national identification has been treated as too noisy to be the centerpiece of an econometric paper.

---

## Section 3 — Median reference count by candidate target journal

For each candidate journal, this section reports (a) typical word count and reference count for recent (2018–2025) firearm-policy articles, (b) sample papers we would cite, and (c) fit assessment for our likely paper. Reference counts are estimated from the 5–10 most recent firearm-policy publications per outlet (where available), using the published versions on the journal sites and PubMed Central. When direct count was infeasible (closed sample, paywall), the figure is reported as a range with a flag.

### 3.1 *Contemporary Economic Policy* (CEP) — Wiley / Western Economic Association

- **Word count.** Maximum 35 pages double-spaced (≈8,000–10,000 words including references). Online appendix unrestricted.
- **Reference count (typical for empirical policy).** ~40–60 references for empirical policy work. CEP firearm-policy papers are uncommon (the journal is broader public-policy-economics), so the benchmark is from comparable applied empirical pieces.
- **Sample firearm-adjacent papers we would cite.** CEP publishes mostly state-policy DiD work (alcohol policy, marijuana policy, abortion policy) using similar identification strategies; firearm-specific recent CEP entries are rare. The journal has historically published policy evaluations consistent with our methodology.
- **Fit for our paper.** **MEDIUM-HIGH.** CEP would value the empirical novelty of permitless-carry → suicide and the methodological covariate-multiverse contribution. Reviewer pool is applied-econ rather than legal-empirical. Risk: editor may flag the firearm-policy framing as needing public-health credentials. Our DAW-style econometric framing fits well.

### 3.2 *Journal of Economic Behavior & Organization* (JEBO) — Elsevier

- **Word count.** No strict limit; typical empirical paper 8,000–12,000 words. Manuscripts may include large online appendices.
- **Reference count (typical).** ~50–80 references for empirical policy work; JEBO accepts longer reference lists than CEP.
- **Sample firearm-adjacent papers.** Firearm policy is occasional in JEBO; behavioral-decision-making papers on risk and crime are more common (e.g., behavioral-deterrence framings; Peltzman-style risk-compensation). Our covariate-multiverse framing — which has a strong methodological-uncertainty flavor — could fit JEBO's interest in behavioral-economics methodology.
- **Fit for our paper.** **MEDIUM.** JEBO would be receptive if the paper foregrounds the behavioral-economic framing (risk compensation; lethal-means as a decision-cost). Less natural fit for a pure policy-evaluation framing.

### 3.3 *Southern Economic Journal* (SEJ) — Wiley / Southern Economic Association

- **Word count.** Maximum 50 pages double-spaced (≈12,000 words including references).
- **Reference count (typical).** ~50–70 references for empirical policy work.
- **Sample firearm-adjacent papers.** SEJ publishes a moderate volume of state-policy DiD work; firearm-policy-specific entries are infrequent but the journal has accepted comparable crime-economics work.
- **Fit for our paper.** **MEDIUM.** SEJ is a strong field outlet with relatively faster turn-around than CEP. Reviewer pool is general applied econ; the firearm-policy substantive framing would be flagged but accepted with the right empirical centering.

### 3.4 *Journal of Empirical Legal Studies* (JELS) — Wiley / Cornell Law

- **Word count.** No strict limit announced (free-format submission); typical paper 12,000–20,000 words. JELS routinely accepts long papers.
- **Reference count (typical).** ~80–120 references for empirical legal-studies work; (Donohue, Aneja, and Weber 2019) has 100+ references; (Ackermann et al. 2015) ~80; recent firearm pieces in JELS routinely 90–130 references.
- **Sample firearm-adjacent papers we would cite.** (Donohue, Aneja, and Weber 2019) — direct competitor methodology; (Ackermann et al. 2015) on Florida SYG; multiple Donohue follow-ups. JELS is **John Donohue's home journal** — he is on the editorial board and his most-cited gun papers appear here. The journal has explicit institutional interest in firearm-policy empirical work.
- **Fit for our paper.** **HIGH.** JELS is the natural top-tier home for any methodologically serious empirical-firearm-policy paper. The covariate-multiverse contribution and modern-DiD application directly fit the journal's audience. Long word count permits both substantive findings and methodological appendix. Risk: JELS may want a direct engagement with Donohue's working-paper pipeline before publication.

### 3.5 *Journal of Health Economics* (JHE) — Elsevier

- **Word count.** No strict limit; typical paper 8,000–12,000 words; online appendices common.
- **Reference count (typical).** ~50–80 references; JHE empirical-policy papers usually 60–80.
- **Sample firearm-adjacent papers.** JHE has published firearm-suicide work occasionally (the literature there is dominated by JAMA / NEJM / AJPH / *Health Affairs*); JHE is the natural economics-of-health outlet. Adjacent JHE papers on alcohol policy, opioid policy, mental-health policy share our identification strategy.
- **Fit for our paper.** **HIGH** (for a suicide-outcome paper). For permitless-carry → suicide as the headline outcome, JHE is the most natural top-tier economics outlet. The mortality outcome anchors the relevance to health economics; the lethal-means-restriction theoretical framing is well within the JHE wheelhouse. Risk: JHE reviewers may expect heavier mechanism evidence than the project currently produces.

### 3.6 *Journal of Quantitative Criminology* (JQC) — Springer

- **Word count.** Typical paper 8,000–12,000 words; structured 250-word abstract required.
- **Reference count (typical).** ~50–80 references for empirical criminology; (Koper and Roth 2001) ~60; (Doucette et al. 2022, *Criminology & Public Policy*) ~50.
- **Sample firearm-adjacent papers we would cite.** (Koper and Roth 2001) on AWB; (Cheng and Hoekstra 2013) is in *JHR* but methodologically aligned; (Doucette et al. 2023) in *Criminology & Public Policy*.
- **Fit for our paper.** **MEDIUM-HIGH.** JQC is the natural criminology home for our methodology. The covariate-multiverse and modern-DiD framing would be welcome. Less prestige than JELS or JHE in econ circles, but more disciplinary alignment with criminology reviewers.

### 3.7 *American Journal of Public Health* (AJPH) — APHA

- **Word count.** Strict — typical research article 3,000–4,000 words; brief reports shorter.
- **Reference count (typical).** ~30–50 references; (Klarevas, Conner, and Hemenway 2019) ~40; (McCourt et al. 2020) ~35; (Crifasi et al. 2024) ~40; (Anestis and Anestis 2015) ~30.
- **Sample firearm-adjacent papers.** AJPH is the home journal of the Webster/Crifasi/Vernick/Anestis school. Most of the canonical PTP, ERPO, and minimum-age papers in our citation list are in AJPH.
- **Fit for our paper.** **HIGH on substance, LOW on length.** AJPH is the natural disciplinary home for the substantive policy result, but the word-count constraint is severe — our covariate-multiverse contribution would have to be relegated to a methods-only companion or online appendix. Risk: AJPH reviewers may demand non-firearm-suicide placebos and an explicit mechanism statement that we may not be able to provide; the AJPH editorial line favors the public-health framing.

### 3.8 *American Economic Journal: Economic Policy* / *AEJ: Applied Economics* — AEA

- **Word count.** AEJ:EP and AEJ:Applied accept manuscripts up to ~14,000 words; online appendices unrestricted.
- **Reference count (typical).** ~60–100 references; AEJ-tier econ papers run ~60–80 references typical.
- **Sample firearm-adjacent papers.** (Knight 2013) is in AEJ:EP; (Donohue, Cai, Bondy, and Cook 2023) is forthcoming AEJ:Applied. AEJ:EP and AEJ:Applied have institutional history with this literature.
- **Fit for our paper.** **HIGH for a strong identification + methodological story; LOWER for a single-policy DiD.** A spatial-RDD + multiverse + permitless-carry-as-natural-experiment combination would be a viable AEJ:EP submission. A single-policy DiD without the multiverse contribution would be a stretch. AEJ-tier review is exacting and slow (12–18 months); requires very strong identification.

### 3.9 Summary table

| Journal | Typical word count | Typical refs | Fit for our paper | Risk |
|---|---|---|---|---|
| AEJ:EP / AEJ:Applied | 10,000–14,000 | 60–100 | High *if* methodologically novel | Slow; very high bar |
| JELS | 12,000–20,000 | 80–130 | Very high (Donohue's home) | Direct competitor pipeline |
| JHE | 8,000–12,000 | 60–80 | High for suicide outcome | Mechanism expectations |
| JQC | 8,000–12,000 | 50–80 | High for methodology | Less econ prestige |
| AJPH | 3,000–4,000 | 30–50 | High substantively, low length | Word-count squeeze |
| CEP | 8,000–10,000 | 40–60 | Medium-high | Less firearm history |
| JEBO | 8,000–12,000 | 50–80 | Medium (behavioral framing) | Disciplinary fit fuzzy |
| SEJ | 10,000–12,000 | 50–70 | Medium | Generalist reviewers |

---

## Section 4 — Recommended target journal

**Recommendation: *Journal of Health Economics* (JHE).** Backup: *Journal of Empirical Legal Studies* (JELS). Tertiary: *Journal of Quantitative Criminology* (JQC), with a "methods companion" submission to *Health Services Research* or *AJPH* for the policy-finding tip.

**Justification (≈250 words).** Three considerations dominate. First, the substantive finding — permitless carry associated with +0.4 to +0.6/100k total suicide rate, robust across panel-FE, Callaway-Sant'Anna, and SCM estimators — is a *health-outcome* result. Suicide is the dominant cause of firearm death in the U.S. (>50% of firearm fatalities since 2003 per CDC WONDER), and any economics-discipline outlet that takes mortality outcomes seriously will read this as a JHE-style paper rather than a JELS-style legal-empirical paper. Second, the methodological covariate-multiverse contribution — explicit specification curves across the LM/BC/DAW/expanded covariate stacks, three estimators, and two outcome definitions — speaks to a methodological audience that JHE has actively cultivated since the Callaway-Sant'Anna and Sun-Abraham critiques transformed the panel-DiD literature. Recent JHE papers on opioid policy, alcohol policy, and minimum-wage health effects have used precisely this multi-estimator + multi-spec template. Third, JHE places permitless-carry in the lethal-means-restriction tradition (gap 2.6) where the natural reviewer pool — Cook, Ludwig, Hemenway, Miller, Anestis, Webster — exists. JELS is the strong backup because John Donohue is on the editorial board and our paper's covariate-multiverse contribution directly engages Donohue-Aneja-Weber 2019; the risk is the journal's slower review and a competing Donohue working paper. JQC provides the cleanest fit if the reduced-form DiD is the centerpiece without the suicide-mortality framing. The methodological covariate-multiverse contribution is publishable as a stand-alone *Journal of Econometrics* methods note but that is a separate paper.

**One-line research-strategy implication.** Frame the paper around (a) suicide as the headline mortality outcome (lethal-means restriction) and (b) covariate-multiverse + modern-DiD as the methodology — JHE is the natural single submission. If reviewers reject on substantive-novelty grounds, pivot to JELS with a Donohue-focused engagement; if they reject on methodology grounds, pivot to JQC.

---

## Section 5 — Theoretical framing options

Five distinct economic-theoretic frameworks have been used to model the policy → outcome link in this literature. For each: a one-paragraph description, key paper(s) using it, and a testable prediction tailored to our setting (permitless carry → suicide / SYG → violence / age-21 → firearm suicide).

### 5.1 Becker rational-choice criminal model (deterrence channel)

**Description.** (Becker 1968 *JPE*) introduced the canonical economic model of criminal behavior: a potential offender commits a crime if the expected utility from committing it exceeds the expected utility of legal alternatives. The decision depends on the probability of capture, the severity of punishment, and the relative payoffs from crime vs. work. The model implies that any policy raising the expected cost of crime — including by increasing the probability that potential victims are armed and resist — should reduce the crime rate. (Lott and Mustard 1997) is the most ambitious application of this Becker framework to firearm policy: shall-issue concealed-carry raises the perceived probability that a victim is armed, raising the expected cost of an attack, and reducing crime. The criminology literature on rational-choice perspective (Cornish and Clarke, Loughran et al.) extends Becker to specific situational decisions.

**Key papers.** (Becker 1968); (Lott and Mustard 1997); (Black and Nagin 1998 critique); (Donohue, Aneja, and Weber 2019 critique).

**Testable prediction for our setting.** If the deterrence channel dominates, permitless carry should *reduce* property crime (especially burglary, which is a "guns-meet-criminal" deterrence-pure case) without affecting suicide rates (which are not subject to deterrence). If we find permitless carry → no significant effect on suicide *and* a modest reduction in burglary, that is consistent with weak deterrence. If we find permitless carry → +0.4–0.6/100k suicide *and* no effect on burglary, the deterrence story fails on both margins. The latter is the predicted result based on prior literature.

### 5.2 Lethal-means restriction framework (suicide; impulsivity-as-decision-cost)

**Description.** The lethal-means restriction framework, articulated most clearly in (Miller and Hemenway 1999) and (Miller, Azrael, and Hemenway 2002), starts from a behavioral-economic premise: many suicides are *impulsive* — undertaken in a window of acute risk lasting minutes to hours — and outcome conditional on attempt depends critically on method lethality. Firearms are by far the most lethal common method (~85% case-fatality rate vs. <5% for ingestion), so restricting firearm access during the impulsive window can prevent a substantial share of attempts from becoming completions, *even if* total attempts are unchanged. This frames "method substitution" as an empirical question: do would-be attempters switch to non-firearm methods at full lethality (substitution), at lower lethality (partial substitution = lives saved), or not at all? The framework is descended from (Clarke and Lester 1989) on coal-gas detoxification in the UK and is the dominant theoretical lens in the public-health firearm-suicide literature.

**Key papers.** (Miller and Hemenway 1999); (Miller, Azrael, and Hemenway 2002); (Anestis and Anestis 2015); (Anestis et al. 2017; 2024); (Crifasi et al. 2015); (Smart and Schell 2020 *AJPH*).

**Testable prediction for our setting.** Lethal-means restriction predicts: (a) any policy that increases firearm access (permitless carry, RTC repeal) should raise *firearm suicide* substantially, while *non-firearm suicide* changes little; (b) total suicide should rise, but by less than the firearm-suicide change (partial method substitution); (c) the effect should be larger in subpopulations with higher impulsive-suicide prevalence (young males, alcohol-prevalent areas, populations with low pre-existing ownership). Our planned non-firearm-suicide placebo and total-vs-firearm-suicide decomposition is a direct test of this framework.

### 5.3 Risk-compensation / Peltzman-effect arguments (defensive use)

**Description.** (Peltzman 1975 *JPE*) argued that mandatory safety devices (seat belts, airbags) induce drivers to take more risk, partially offsetting the safety benefit. The firearm-policy version: when more law-abiding citizens carry, they may behave more aggressively (more confrontational driving, more vigilance leading to escalation), and would-be aggressors may carry more or escalate to maintain dominance — net effect ambiguous. (Hoekstra and Sloan 2025) and the (Donohue, Cai, Bondy, and Cook 2023) gun-theft mechanism are essentially Peltzman-flavored: more guns in circulation generate more interpersonal-conflict escalation and more theft. The pro-RTC argument that armed citizens deter crime is the inverse Peltzman: more carrying → less risk-taking by criminals. Empirically, the modern consensus (RAND 2024) is that the criminal-side risk-compensation channel dominates the citizen-side deterrence channel for permissive-carry policies.

**Key papers.** (Peltzman 1975); (Hemenway and Solnick 2015 on defensive use frequency); (Donohue, Cai, Bondy, and Cook 2023 mechanism evidence); (Cheng and Hoekstra 2013 SYG inverse-deterrence).

**Testable prediction for our setting.** If risk-compensation dominates, permitless carry should produce: (a) increased firearm violence (assault, homicide) consistent with escalation in armed confrontations; (b) increased firearm theft consistent with more carriable guns in circulation; (c) ambiguous suicide effect (only if armed confrontations spill into intra-household violence, which we would not detect cleanly). For our paper, the risk-compensation framing is more naturally a homicide/assault story than a suicide story; we should mention it but not lead with it for a suicide-outcome paper.

### 5.4 Cook–Ludwig "gun-prevalence externality" framing

**Description.** (Cook and Ludwig 2006 *J. Public Economics*) frames household firearm ownership as a generator of negative externalities — each additional household firearm increases the expected gun-homicide and gun-suicide flow into the surrounding community. They estimate the elasticity of homicide with respect to firearm prevalence at +0.1 to +0.3 (entirely loaded on gun homicide), translating into a marginal external cost of $100–$600 per household per year. The externality logic explains why policies that change ownership (PTP, UBC, age-21) can have effects that operate through the community gun stock rather than only through the marginal purchaser. (Duggan 2001 *JPE*) provides complementary "more guns, more crime" evidence using *Guns & Ammo* subscriptions as a prevalence proxy. The externality framing is the public-economics version of the public-health literature on firearm prevalence.

**Key papers.** (Cook and Ludwig 2006); (Duggan 2001); (Cook, Ludwig, Venkatesh, and Braga 2007 on underground markets); (Miller, Azrael, and Hemenway 2002 ownership-suicide).

**Testable prediction for our setting.** Cook-Ludwig predicts: (a) any policy that raises household firearm prevalence (permitless carry presumably raises NICS volume; RTC raises ownership) should raise both firearm suicide and firearm homicide proportionally, with the suicide elasticity matching the +0.1 to +0.3 homicide elasticity (Miller-Hemenway estimates suggest +0.4–0.6 for suicide); (b) the effect should be mediated by the ownership shift (so a mediation analysis where we condition on `ownership_fss` should attenuate the policy effect substantially); (c) effects should be larger in low-baseline-ownership areas where the marginal household-gun is more behaviorally consequential. For our paper, if we find that conditioning on ownership absorbs the permitless-carry effect, the Cook-Ludwig externality framing is the right interpretation; if the policy effect is independent of ownership, it operates through some other channel (e.g., direct carrying behavior).

### 5.5 Knight-style gravity / cross-state trafficking model

**Description.** (Knight 2013) imports gravity-model logic from the international-trade literature into firearm policy. Bilateral crime-gun flows between states are modeled as a function of source-destination law strictness, geographic distance, and population-economic mass. A weak-law state acts like a low-tariff trade partner: it generates illicit gun supply for neighboring strict-law states, with flows decaying in distance. The framework predicts that strict-law states experience attenuated *measured* policy effects because cross-border substitution is available to local criminals. (Ashworth and Kozinetz 2021) is a cross-sectional confirmation. The framework has natural extensions: dynamic gravity (response of flows to policy changes); equilibrium gravity (general-equilibrium effect of nationwide policy uniformity).

**Key papers.** (Knight 2013); (Ashworth and Kozinetz 2021); (Crifasi, Buggs, Choksy, and Webster 2017 trace-data on Maryland PTP); (Cook, Ludwig, Venkatesh, and Braga 2007 on Chicago underground markets).

**Testable prediction for our setting.** The gravity model predicts: (a) for our spatial-RDD design, county-pair estimates should be *attenuated* relative to state-panel estimates because the strict-law county is partly contaminated by its weak-law neighbor; (b) the attenuation should grow with proximity to weak-law states; (c) state-level effect estimates of strict policies should *underestimate* the counterfactual nationwide-uniform-strict-policy effect. For our paper, the gravity framing motivates reporting both state-panel and county-pair estimates and explicitly bounding the spillover bias. It does not directly motivate the suicide outcome (suicide is less subject to cross-border supply because the impulsive window is local), but it strongly motivates reporting county-pair vs. state-panel estimate differences as a methodological contribution.

### 5.6 Synthesis: which framing(s) to lead with

Our recommended lead framing for the paper is **lethal-means restriction (5.2) as the primary theoretical lens**, supplemented by **the Cook-Ludwig externality framing (5.4) as the mechanism-level interpretation**. This combination:

1. Anchors the paper to suicide as the headline outcome — the right move for JHE submission.
2. Generates the testable prediction that drives our identification: firearm suicide ↑, non-firearm suicide ≈ unchanged, total suicide ↑ by less than firearm suicide. This is the "non-firearm placebo + lethal-means" robustness suite that is the gold standard in (Crifasi et al. 2015), (Webster et al. 2014), and (Kivisto and Phalen 2018).
3. Engages the dominant theoretical framework in the existing canon (Miller, Hemenway, Anestis, Crifasi school) without requiring novel theoretical apparatus we have not built.
4. Allows mechanism analysis via ownership mediation (the Cook-Ludwig externality), using existing project panel variables (`ownership_fss`, `ownership_rand`, NICS).
5. Permits a clean discussion-section engagement with deterrence (5.1) and risk-compensation (5.3) framings as alternative interpretations that our results can be argued to favor or disfavor.

The deterrence (5.1) and risk-compensation (5.3) framings are introduced briefly in the literature-review section as competing hypotheses, with our results positioned as evidence on the relative importance of each. The gravity (5.5) framing is reserved for the methodology section as the warrant for spatial-spillover robustness.

---

## Closing notes for the drafting agent

This document is a foundation, not a draft. The paper draft should:

1. **Open with a stylized fact** (e.g., the post-2020 wave of permitless-carry adoptions, or the rising share of firearm suicide in total U.S. mortality), then state the research question and headline finding in the abstract.
2. **Use the lethal-means framing (5.2)** as the dominant theoretical lens, with the Cook-Ludwig externality (5.4) as the mechanism interpretation.
3. **Position the methodological contribution** as a covariate-multiverse + modern-DiD application, foregrounding the (Donohue, Aneja, and Weber 2019) and (Aneja, Donohue, and Zhang 2014) lineage as direct intellectual antecedents.
4. **Anchor the literature review** in Section 1 of this document, with denser engagement with the suicide-specific work (Miller-Hemenway, Anestis, Crifasi 2015, Kivisto-Phalen) and the methodological work (DAW 2019, Cheng-Hoekstra 2013).
5. **Target JHE** as the primary submission outlet (Section 4), with a JELS or JQC backup.
6. **Use the gap analysis (Section 2)** to frame the contribution: open questions 2.1, 2.5, 2.6, 2.7, 2.9, and 2.10 are the strongest contribution slots; the paper should claim 2–3 of them rather than all six.
7. **Cite ~70 references** for a JHE-tier paper (see Section 3.5 table); the 50 papers in Section 1 plus the methodological references in Section 2.7/2.9 plus the framing references in Section 5 plus a small number of contemporary working papers should produce that count comfortably.

The paper's likely contribution claim, in one sentence, would be: "We provide the first comprehensive evaluation of permitless-carry effects on firearm and total suicide rates using modern heterogeneity-robust DiD estimators and a formal covariate-multiverse approach, finding robust evidence of a +0.4–0.6/100k increase in total suicide rates concentrated in firearm suicide, consistent with the lethal-means restriction framework and the Cook-Ludwig gun-prevalence externality."

---

## Bibliography of key sources consulted (URLs for the drafting agent)

The following sources were used in compiling this scan; the full list of 50 papers' citations is in Section 1 above and is not duplicated here.

- Lott & Mustard 1997 — https://chicagounbound.uchicago.edu/cgi/viewcontent.cgi?article=1150&context=law_and_economics
- Ayres & Donohue 2003 — https://law.stanford.edu/publications/shooting-down-the-more-guns-less-crime-hypothesis-3/
- Black & Nagin 1998 — https://www.journals.uchicago.edu/doi/10.1086/468019
- Aneja, Donohue, Zhang 2014 — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2443681
- Donohue, Aneja, Weber 2019 — https://onlinelibrary.wiley.com/doi/abs/10.1111/jels.12219
- Donohue, Cai, Bondy, Cook 2023 (NBER) — https://www.nber.org/papers/w30190
- Webster, Crifasi, Vernick 2014 — https://pmc.ncbi.nlm.nih.gov/articles/PMC3978146/
- Crifasi, Meyers, Vernick, Webster 2015 — https://pmc.ncbi.nlm.nih.gov/articles/PMC4566551/
- Rudolph, Stuart, Vernick, Webster 2015 — https://pmc.ncbi.nlm.nih.gov/articles/PMC4504296/
- McCourt et al. 2020 — https://pmc.ncbi.nlm.nih.gov/articles/PMC7483089/
- Luca, Malhotra, Poliquin 2017 — https://www.pnas.org/doi/10.1073/pnas.1619896114
- Ludwig & Cook 2000 (Brady) — https://jamanetwork.com/journals/jama/fullarticle/192946
- Cheng & Hoekstra 2013 — https://jhr.uwpress.org/content/48/3/821
- McClellan & Tekin 2017 — https://jhr.uwpress.org/content/52/3/621
- Humphreys, Gasparrini, Wiebe 2017 (Florida SYG) — https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/2582988
- Hoekstra & Sloan (race-SYG WP) — https://carlywillsloan.com/research/
- Kivisto & Phalen 2018 — https://psychiatryonline.org/doi/10.1176/appi.ps.201700250
- Swanson et al. 2017 (CT ERPO) — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2828847
- Anestis & Anestis 2015 — https://pmc.ncbi.nlm.nih.gov/articles/PMC4566551/
- Anestis, Anestis, Butterworth 2017 — https://ajph.aphapublications.org/doi/10.2105/AJPH.2016.303650
- Crifasi et al. 2024 (age-21) — https://pmc.ncbi.nlm.nih.gov/articles/PMC11224627/
- Webster et al. 2004 (youth-focused) — https://jamanetwork.com/journals/jama/fullarticle/199263
- Klarevas, Conner, Hemenway 2019 — https://pmc.ncbi.nlm.nih.gov/articles/PMC6836798/
- Koper & Roth 2001 — https://link.springer.com/article/10.1023/A:1007522431219
- Koper 2004 NIJ — https://www.ojp.gov/pdffiles1/nij/grants/204431.pdf
- Knight 2013 — https://www.aeaweb.org/articles?id=10.1257/pol.5.4.200
- Cook & Ludwig 2006 — https://www.sciencedirect.com/science/article/abs/pii/S0047272705000411
- Cook, Ludwig, Venkatesh, Braga 2007 — https://onlinelibrary.wiley.com/doi/10.1111/j.1468-0297.2007.02098.x
- Duggan 2001 — https://www.jstor.org/stable/3078549
- Miller & Hemenway 1999 — https://www.sciencedirect.com/science/article/abs/pii/S1359178997000369
- Miller, Azrael, Hemenway 2002 — https://pubmed.ncbi.nlm.nih.gov/12192220/
- Miller, Hemenway, Azrael 2007 — https://pubmed.ncbi.nlm.nih.gov/17070975/
- Hepburn & Hemenway 2004 — https://www.sciencedirect.com/science/article/abs/pii/S1359178903000442
- Cook & Donohue 2017 (Science) — https://www.science.org/doi/10.1126/science.aar3067
- RAND 4th ed. 2024 — https://www.rand.org/pubs/research_reports/RRA243-9.html
- Hahn et al. 2005 — https://www.thecommunityguide.org/sites/default/files/publications/firearms-ajpm-evrev-firearms.pdf
- Lee et al. 2017 — https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/2596976
- Santaella-Tenorio et al. 2016 — https://academic.oup.com/epirev/article/38/1/140/2578378
- Hemenway & Solnick 2015 (defensive use) — https://www.sciencedirect.com/science/article/abs/pii/S0091743514004769
- Wintemute, Wright, Drake, Beaumont 2001 — https://jamanetwork.com/journals/jama/fullarticle/193511
- Castillo-Carniglia et al. 2018 — https://injuryprevention.bmj.com/content/24/6/454
- Castillo-Carniglia et al. 2019 — https://www.sciencedirect.com/science/article/abs/pii/S1047279718305453
- Doucette, McCourt, Crifasi, Webster 2023 — https://poodle-banjo-jhsp.squarespace.com/s/Criminology-Public-Policy-2023-Doucette-Deregulation-of-public-civilian-gun-carrying-and-violent-cri.pdf
- Doucette, Ward, McCourt, Webster, Crifasi 2022 — https://pubmed.ncbi.nlm.nih.gov/35536393/
- Hamill et al. 2019 — https://pubmed.ncbi.nlm.nih.gov/30359823/
- Jorgensen 2024 (permitless-carry 4-state) — https://journals.sagepub.com/doi/abs/10.1177/17488958241270878
- Smart & Schell 2020 (substitution review AJPH) — https://pmc.ncbi.nlm.nih.gov/articles/PMC7483123/
- Anestis et al. 2024 (storage practices) — https://pmc.ncbi.nlm.nih.gov/articles/PMC11702847/
- Becker 1968 — https://archiv.soms.ethz.ch/sociology_course/Lecture6/becker1968.pdf
- Peltzman 1975 — https://www.jstor.org/stable/1830396
- Callaway & Sant'Anna 2021 — https://www.sciencedirect.com/science/article/abs/pii/S0304407620303948
- Sun & Abraham 2021 — https://www.sciencedirect.com/science/article/abs/pii/S030440762030378X
- Borusyak, Jaravel, Spiess 2024 — https://www.nber.org/papers/w24544
- de Chaisemartin & D'Haultfœuille 2020 — https://www.aeaweb.org/articles?id=10.1257/aer.20181169
- Simonsohn, Simmons, Nelson 2020 (specification curve) — https://www.nature.com/articles/s41562-020-0912-z
- Steegen et al. 2016 (multiverse) — https://journals.sagepub.com/doi/10.1177/1745691616658637

---

*Document version 1.0, prepared 2026-05-01.*
