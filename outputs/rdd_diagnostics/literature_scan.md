# Literature Scan: Spatial RDD / Border-County Designs for U.S. Firearm Policy

**Project context.** This methodology document supports a spatial regression-discontinuity (RDD) analysis of U.S. firearm policy effects that exploits state-border county pairs as the identifying variation. The lit scan below establishes (i) the methodological lineage we are adapting from labor economics, (ii) the canonical firearm applications of the same identification logic, and (iii) the most credible recent firearm-policy designs that use either contiguous-county comparisons, synthetic controls, or panel difference-in-differences specifications close to ours.

## Prose summary (≈360 words)

The contiguous-county-pair design used by Dube, Lester, and Reich (DLR, 2010) is the workhorse identification strategy this project adapts. DLR confines identification to within-pair, within-time variation — every adjacent county pair straddling a state border becomes its own experiment, absorbing local shocks with a saturated set of pair × period fixed effects and two-way clustered SEs (state and border-segment). The logic transports cleanly to firearm policy because state borders sharply discontinue firearm law while leaving demographics, labor markets, and crime opportunities approximately continuous.

The closest direct firearm analog is Knight (2013), which exploits the same border geography but on the dependent-variable side: ATF crime-gun trace data show that source-state weakness in firearm law generates measurable cross-state externalities, and flows decay sharply with distance. Knight is the canonical warrant for treating border counties as partly treated by their *neighbor's* policy — a spillover correction we will need to confront.

The Johns Hopkins group (Webster–Vernick–Crifasi) anchors the policy-evaluation side using state-level synthetic control. Their work on Missouri's 2007 permit-to-purchase (PTP) repeal and Connecticut's 1995 PTP adoption is the most-cited applied evidence on handgun-licensing effects, replicated across four states in AJPH 2020. These are not RDD papers, but they share the contiguous-state donor-pool intuition and provide the effect-size benchmarks against which our county-pair estimates will be judged.

Three more recent papers round out the frame. Donohue–Aneja–Weber (2019) shows SCM RTC effects survive donor-pool and placebo robustness — and triggers the Lott/Donohue exchange that any RTC-adjacent finding inherits. Luca–Malhotra–Poliquin (2017, PNAS) on waiting periods uses state-panel two-way FE plus the 1994 Brady Act federal natural experiment. Kivisto–Phalen (2018) applies the same toolkit to red-flag/ERPO laws. Ashworth–Kozinetz (2021) is the closest pure border-distance firearm design — county-level proximity to weak-law states predicts homicide rates, validating Knight's spillover concern but with a thin cross-sectional design our DiD would improve on. Cross-cutting reviewer friction: (a) clustering choice, (b) donor-pool composition, (c) non-firearm placebos, (d) cross-border purchasing attenuation.

---

## Per-paper entries

### 1. Dube, Lester, & Reich (2010, *Review of Economics and Statistics*) — METHODOLOGICAL LODESTAR

- **Cite.** Dube, A., Lester, T.W., & Reich, M. (2010). "Minimum Wage Effects Across State Borders: Estimates Using Contiguous Counties." *RESTAT* 92(4): 945–964. (User's brief listed *RES*; actual outlet is *RESTAT*.)
- **Design.** Contiguous county-pair panel DiD; ~1,181 cross-border pairs stacked as pair × quarter; county FE + pair × period FE.
- **Bandwidth.** Non-parametric — only counties immediately adjacent to a border qualify; pair is the comparison unit. Sample 1990Q1–2006Q2.
- **Outcomes.** Restaurant employment and earnings, low-wage employment shares (QCEW).
- **Finding.** No significant disemployment effect; positive earnings effect. State-panel specs without pair FE generate spurious negatives from spatial trend heterogeneity.
- **Gotcha.** Neumark, Salas & Wascher (2014) argued pair-FE absorbs too much identifying variation and that two-way (state + border-segment) clustering is anti-conservative. DLR rejoinder + Dube, Manning, Naidu et al. (NBER w32901, 2024) defend. *For us:* expect symmetric pushback on pair × year FE absorbing too much firearm-policy variation, and on clustering dimension.

### 2. Knight (2013, *AEJ: Economic Policy*) — DIRECT FIREARM ANALOG

- **Cite.** Knight, B. (2013). "State Gun Policy and Cross-State Externalities: Evidence from Crime Gun Tracing." *AEJ: EP* 5(4): 200–229. (User's brief said *AEJ: Applied*; correct outlet is *AEJ: EP*. NBER w17469.)
- **Design.** Gravity-style bilateral state-pair specification on 2009 ATF trace data (N=145,321 guns; 50×50 state pairs).
- **Bandwidth.** Continuous log distance between state centroids — not a sharp RDD bandwidth. ID assumption: bilateral trafficking flows respond to the gradient in source-vs-destination law strictness.
- **Outcomes.** Inter-state crime-gun flows; destination-state criminal possession rates.
- **Finding.** Guns flow weak→strict; decay with distance, confirming spatial externalities. Strict-state criminal possession is partly explained by neighbors' weak laws.
- **Gotcha.** Trace data are non-random (only recovered, successfully traced guns; biased toward older guns / certain crimes). *For us:* Knight is the warrant for treating border counties as partly treated by the *neighbor's* policy — the spillover bias we must bound.

### 3. Webster, Crifasi, & Vernick (2014, *Journal of Urban Health*) — MISSOURI PTP REPEAL

- **Cite.** Webster, D.W., Crifasi, C.K., & Vernick, J.S. (2014). "Effects of the Repeal of Missouri's Handgun Purchaser Licensing Law on Homicides." *J Urban Health* 91(2): 293–302.
- **Design.** Synthetic control (SCM). Treated = Missouri (2007 PTP repeal); donor pool = states without major firearm-law changes 1999–2010.
- **Bandwidth.** Pre 1999–2007; post 2008–2010 (vital stats) and 2008–2012 (UCR).
- **Outcomes.** Firearm homicide; non-firearm homicide (placebo).
- **Finding.** Repeal associated with +1.09/100k firearm homicides (+23%, vital stats); +0.93/100k (+16%, UCR). No effect on non-firearm homicides — firearm-specific channel.
- **Gotcha.** Reviewers probe whether neighbor states (themselves affected via cross-border flow) should be excluded from the donor pool; authors excluded own-law changers but didn't formally bound spillover contamination. *For us:* adopt the non-firearm placebo template.

### 4. Crifasi et al. (2015, *Preventive Medicine*) + Rudolph et al. (2015, *AJPH*) — CONNECTICUT PTP

- **Cite.** Crifasi, C.K., Meyers, J.S., Vernick, J.S., & Webster, D.W. (2015). *Preventive Medicine* 79: 43–49 (suicides). Rudolph, Stuart, Vernick & Webster (2015), *AJPH* 105(8) (homicides).
- **Design.** SCM on CT post-1995 PTP adoption.
- **Bandwidth.** Pre 1981–1994; post 1995–2005 (10-yr window). Donor pool = states without major handgun laws.
- **Outcomes.** Firearm suicide and firearm homicide; non-firearm placebos.
- **Finding.** ~15% reduction in firearm suicides; ~40% reduction in firearm homicides over 10 years. No effect on non-firearm rates.
- **Gotcha.** Effect size large and front-loaded; sensitive to coding the intervention year (1995 vs. actual enforcement onset). Donor weights unstable; RMSPE placebo distributions wide. *For us:* benchmarks the effect-size *magnitude* expected from PTP-style interventions.

### 5. McCourt, Crifasi, Stuart, Vernick, et al. (2020, *AJPH*) — 4-STATE REPLICATION

- **Cite.** "Purchaser Licensing, Point-of-Sale Background Check Laws, and Firearm Homicide and Suicide in 4 US States, 1985–2017." *AJPH* 110(10): 1546–1552.
- **Design.** Multi-state SCM (CT, MD, PA, MO) — state-by-state effects of adopting/repealing PTP and point-of-sale UBC laws.
- **Bandwidth.** Long pre-periods (back to 1985); donor pool excludes own-law changers.
- **Outcomes.** Firearm homicide; firearm suicide.
- **Finding.** PTP associated with ~27.8% reduction in CT firearm homicide; MO repeal associated with +47.3% firearm homicide and +23.5% firearm suicide. UBC alone (without PTP) shows weaker, less consistent effects.
- **Gotcha.** RAND evidence reviews classify UBC effects as inconclusive — reviewers question pooling across heterogeneous law texts. *For us:* recent benchmark that PTP > UBC alone in expected effect size.

### 6. Donohue, Aneja, & Weber (2019, *JELS*) — RTC SYNTHETIC CONTROL

- **Cite.** Donohue, J.J., Aneja, A., & Weber, K.D. (2019). *JELS* 16(2): 198–247. NBER w23510.
- **Design.** State-panel two-way FE through 2014, plus state-level SCM for each RTC adopter.
- **Bandwidth.** SCM uses 10-year pre/post windows; donor pool restricted to non-RTC or late-adopting states. Panel 1977–2014.
- **Outcomes.** Aggregate violent crime; murder; rape; robbery; aggravated assault.
- **Finding.** RTC associated with 13–15% increase in violent crime 10 years post-adoption — directly contradicts Lott–Mustard "more guns, less crime."
- **Gotcha.** Latest round of Ayres–Donohue (2003, *Stanford LR*) vs. Lott exchange; Econ Journal Watch comments push back on SCM donor weights and RTC adoption-year coding. *For us:* dominant template for SCM as robustness check on county-pair DiD; plan to run both.

### 7. Luca, Malhotra, & Poliquin (2017, *PNAS*) — WAITING PERIODS

- **Cite.** Luca, M., Malhotra, D., & Poliquin, C. (2017). *PNAS* 114(46): 12162–12165.
- **Design.** State-panel two-way FE on all waiting-period changes 1970–2014, plus a quasi-experimental wedge from the 1994 Brady Act, which imposed a temporary federal waiting period on the ~32 states without pre-existing background check infrastructure.
- **Bandwidth.** Full state panel; Brady-Act subset for stronger ID.
- **Outcomes.** Gun homicides; gun suicides.
- **Finding.** Waiting periods reduce gun homicides by ~17%; gun suicides by ~7–11%. Brady subset consistent.
- **Gotcha.** Kleck (2017, SSRN) alleged selective specification reporting and that Brady-affected states differed systematically. *For us:* template for combining state-panel FE with a federal-policy natural experiment; reminder that positive findings in this literature draw hostile scrutiny.

### 8. Kivisto & Phalen (2018, *Psychiatric Services*) — RED-FLAG / ERPO LAWS

- **Cite.** Kivisto, A.J., & Phalen, P.L. (2018). *Psychiatric Services* 69(8): 855–862.
- **Design.** SCM for CT (1999 ERPO) and IN (2005 ERPO) suicide rates, with DiD sensitivity and randomization-inference placebos.
- **Bandwidth.** Pre 1981→law adoption; post through 2015. Donor pool = 50 states minus treated.
- **Outcomes.** Firearm suicide; non-firearm suicide (placebo).
- **Finding.** IN: −7.5% firearm suicide. CT: −1.6% immediately post-1999, growing to −13.7% post-Virginia-Tech (2007) when enforcement intensified. Firearm-specific.
- **Gotcha.** CT effect is enforcement-conditional, complicating ITT framing; reviewers question whether the post-2007 jump is the law or behavioral-health awareness. *For us:* non-firearm placebo + randomization inference templates; enforcement-intensity caveat foreshadows our "law on books vs. on street" concern.

### 9. Ashworth & Kozinetz (2021, *Preventive Medicine Reports*) — EXPLICIT BORDER-DISTANCE FIREARM DESIGN

- **Cite.** Ashworth, T.R., & Kozinetz, C.A. (2021). *Preventive Medicine Reports* 22: 101369.
- **Design.** County-level cross-section parameterizing distance from each strict-law county to the nearest weak-law state (no UBC/BCS/PTP). Negative-binomial regression with demographic covariates.
- **Bandwidth.** Continuous distance variable, not a sharp bandwidth; strict-state counties only; 2014–2017.
- **Outcomes.** County firearm homicide rate.
- **Finding.** Border distance negatively associated with firearm homicide (p = 0.009) in pooled model — closer to weak-law states means *higher* firearm homicides — but loses significance in stratified models with sparse cells.
- **Gotcha.** Cross-sectional (no policy variation over time), so confounding is a major concern; small-cell instability in subsets. *For us:* the closest prior to what we are doing — validates the geographic-spillover signal but the cross-sectional design is exactly the gap our county-pair DiD fills.

---

## Cross-cutting reviewer-friction (for our methodology section)

1. **Clustering.** DLR's two-way (state + border-segment) is contested; report state-only, pair, and border-segment one-way as robustness.
2. **Spillover.** Knight implies neighbors are partly treated via gun flows; need a Conley-style spatial SE or explicit spillover term.
3. **Non-firearm placebo.** Webster/Crifasi and Kivisto both use it; pre-commit.
4. **Donor pool.** Pre-register the rule if SCM is run as robustness.
5. **Lott/Donohue legacy.** RTC-adjacent findings inherit the long Ayres–Donohue vs. Lott exchange; plan a full robustness battery.

---

## Sources

- Dube, Lester, Reich (2010): https://direct.mit.edu/rest/article/92/4/945/57855/ ; https://escholarship.org/uc/item/86w5m90m
- Neumark/Wascher critique reassessment (NBER w32901, 2024): https://www.nber.org/papers/w32901
- Knight (2013), AEJ:EP: https://www.aeaweb.org/articles?id=10.1257/pol.5.4.200 ; NBER w17469: https://www.nber.org/papers/w17469
- Webster, Crifasi, Vernick (2014): https://pmc.ncbi.nlm.nih.gov/articles/PMC3978146/
- Crifasi, Meyers, Vernick, Webster (2015), Preventive Medicine: https://www.sciencedirect.com/science/article/abs/pii/S0091743515002297
- Rudolph, Stuart, Vernick, Webster (2015), AJPH (CT homicides): https://pmc.ncbi.nlm.nih.gov/articles/PMC4504296/
- 4-state SCM, AJPH 2020: https://ajph.aphapublications.org/doi/full/10.2105/AJPH.2020.305822 ; https://pmc.ncbi.nlm.nih.gov/articles/PMC7483089/
- Donohue, Aneja, Weber (2019), JELS: https://onlinelibrary.wiley.com/doi/abs/10.1111/jels.12219 ; NBER w23510: https://www.nber.org/papers/w23510
- Donohue, Cai, Bondy, Cook (2022), NBER w30190 (RTC mechanisms): https://www.nber.org/papers/w30190
- Ayres & Donohue (2003), Stanford LR: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=351428
- Luca, Malhotra, Poliquin (2017), PNAS: https://www.pnas.org/doi/10.1073/pnas.1619896114
- Kleck comment on LMP: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3084706
- Kivisto & Phalen (2018), Psychiatric Services: https://psychiatryonline.org/doi/10.1176/appi.ps.201700250
- Ashworth & Kozinetz (2021), Preventive Medicine Reports: https://pmc.ncbi.nlm.nih.gov/articles/PMC8435077/
- RAND Gun Policy in America (evidence reviews used as cross-reference): https://www.rand.org/research/gun-policy.html
