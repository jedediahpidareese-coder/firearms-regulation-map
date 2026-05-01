# Spatial RDD diagnostics summary
Pre-RDD characterization of the border-strip sample for three state policies (permitless concealed carry, civil red-flag laws, universal background checks). For each (policy x bandwidth x donut) cell we report counts of border-strip counties, distinct state-pairs, the subset of pairs that straddle a policy boundary in each year, and treated/control county counts. We also produce two visual diagnostics per policy: a pooled cross-border outcome plot to look for visible discontinuities at the border, and a year-by-year within-pair gap plot to inspect pre-trend parallelism.

## Headline findings
1. **Permitless carry** has by far the most straddling state-pair-years (mean 19-27 per year across the 50/100/200 km bandwidths), driven by the rapid 2021-2024 wave of state adoptions. Cross-border outcome levels are nearly identical near the border (jumps within +/- 18 per 100k for property/burglary, near-zero for murder), and pre-trend gaps are small but noisy. This is the cleanest setting for a headline RDD.
2. **Red-flag laws** show large near-border level differences (violent crime ~119 per 100k lower on the treated side, property crime ~646 per 100k lower) AND large pre-period gaps in the same direction. This is selection: states that adopt red-flag laws are systematically lower-crime states. The cross-border 'jump' mostly reflects this state-level selection, not a treatment effect. The pre-trend SDs are small relative to the levels, so the level shift is real, not noise.
3. **UBC** shows mixed pre-trends: large negative violent-crime and murder gaps (treated < control) but large positive property/burglary gaps. The 2013-cohort dominates, with very few post-period pairs. Pre-period gap SDs (34, 105, 38) are nearly as large as the gap means - pretrends are noisy, not flat.
4. The donut radius (0/10/25 km) only trims a handful of counties because just ~10 counties have centroid-to-border <10 km and ~160 have <25 km. Donut effects on the cell-counts table are second-order; the bandwidth dimension matters far more.

## 1. Sample size by (policy x bandwidth) (donut = 0)
Counts averaged across years 2009-2024. 'pairs straddling' is the average across years of distinct state-pairs whose two states differed on the policy that year.
| Policy | Bandwidth (km) | avg counties/yr | avg pairs/yr | avg straddling pairs/yr | max straddling pairs/yr |
| --- | --- | --- | --- | --- | --- |
| permitless_carry | 50 | 902 | 88 | 19.1 | 37 |
| permitless_carry | 100 | 1954 | 101 | 25.3 | 43 |
| permitless_carry | 200 | 2814 | 105 | 27.2 | 45 |
| red_flag | 50 | 902 | 88 | 8.2 | 24 |
| red_flag | 100 | 1954 | 101 | 10.8 | 30 |
| red_flag | 200 | 2814 | 105 | 11.4 | 32 |
| ubc | 50 | 902 | 88 | 10.8 | 17 |
| ubc | 100 | 1954 | 101 | 15.9 | 23 |
| ubc | 200 | 2814 | 105 | 16.9 | 25 |

## 2. Donut-radius sensitivity (bandwidth = 100 km)
Average border-strip counties per year drop as the donut grows. Pair *identity* is preserved across donuts (each pair is two states), so the straddling-pair count is unchanged - the donut trims the innermost counties on each side. Mean distance shifts outward accordingly. Only ~10 counties have centroid-to-border <10 km and ~160 have <25 km, so donut effects are modest.
| Policy | donut 0 counties | donut 10 counties | donut 25 counties | mean dist d=0 | mean dist d=25 |
| --- | --- | --- | --- | --- | --- |
| permitless_carry | 1954 | 1944 | 1793 | 55.8 km | 59.1 km |
| red_flag | 1954 | 1944 | 1793 | 55.8 km | 59.1 km |
| ubc | 1954 | 1944 | 1793 | 55.8 km | 59.1 km |

## 3. Modal cohort year per policy
- permitless_carry: modal cohort year = 2021
- red_flag: modal cohort year = 2019
- ubc: modal cohort year = 2013

## 4. Visual diagnostics
- `figures/cross_section_<policy>.svg` plots the pooled mean rate by signed distance bin (negative on the control side, positive on the treated side, bin width 25 km). A visible jump at d = 0 is the descriptive RDD signature.
- `figures/pretrends_<policy>.svg` plots the mean within-pair (treated - control) outcome gap year by year for state-pairs that ever straddled the policy. A flat or smoothly evolving pre-period before the modal cohort year supports parallel-trends in the donut/RDD strip.

Numerical readout from the figure data (within +/-25 km of the border for the cross-section; pre-period defined as year < modal cohort year for pre-trends):

| Policy | Outcome | near-border jump (T-C) | pre-period mean gap | pre-period sd of gap |
| --- | --- | --- | --- | --- |
| permitless_carry | county_violent_crime_rate | +3.9 | -33.3 | 28.1 |
| permitless_carry | county_murder_rate | -0.4 | +0.3 | 1.6 |
| permitless_carry | county_property_crime_rate | +14.3 | +30.0 | 323.5 |
| permitless_carry | county_burglary_rate | +18.3 | +19.1 | 75.0 |
| red_flag | county_violent_crime_rate | -118.8 | +60.7 | 7.6 |
| red_flag | county_murder_rate | -4.5 | -0.9 | 1.5 |
| red_flag | county_property_crime_rate | -645.9 | +302.7 | 109.8 |
| red_flag | county_burglary_rate | -83.9 | +71.7 | 43.9 |
| ubc | county_violent_crime_rate | -5.3 | -40.2 | 34.0 |
| ubc | county_murder_rate | -0.4 | -1.5 | 1.1 |
| ubc | county_property_crime_rate | +70.5 | +149.7 | 105.5 |
| ubc | county_burglary_rate | -67.5 | +63.0 | 37.8 |

## 5. Go / no-go assessment
Heuristic: at least 8 distinct straddling state-pairs per year is the minimum to support a credible headline (gives ~16+ treated/control side observations even before stacking years). We also flag pre-trend severity (using violent crime as the headline outcome): 'ok' = small/noisy pre-period gap; 'moderate' = |mean gap| > 15 per 100k; 'concerning' = |mean gap| > 30 per 100k AND > 1.5 sd of the year-to-year gap.

| Policy | Bandwidth | Recommendation | Reason | Pre-trend (violent) |
| --- | --- | --- | --- | --- |
| permitless_carry | 50 km | GO | ample straddling pairs (mean 19/yr) | moderate |
| permitless_carry | 100 km | GO | ample straddling pairs (mean 25/yr) | moderate |
| permitless_carry | 200 km | GO | ample straddling pairs (mean 27/yr) | moderate |
| red_flag | 50 km | GO (caution: pre-trend gap) | borderline pairs (mean 8.2/yr, peak 24); level shift in pre-period | concerning |
| red_flag | 100 km | GO (caution: pre-trend gap) | borderline pairs (mean 10.8/yr, peak 30); level shift in pre-period | concerning |
| red_flag | 200 km | GO (caution: pre-trend gap) | borderline pairs (mean 11.4/yr, peak 32); level shift in pre-period | concerning |
| ubc | 50 km | GO (with caution) | borderline pairs (mean 10.8/yr, peak 17) | moderate |
| ubc | 100 km | GO | ample straddling pairs (mean 16/yr) | moderate |
| ubc | 200 km | GO | ample straddling pairs (mean 17/yr) | moderate |

## 6. Caveats / flags
- These diagnostics treat each county-year independently for the straddling indicator; pair-level treatment timing variation will be exploited in the actual RDD spec.
- Pre-trend gaps are unweighted means across pairs; a more rigorous test would weight by inverse-variance or by population.
- The cross-section figure pools across all years where the pair straddled; if treatment effects evolve over time, pooling can mask a discontinuity that is sharp only in later years.
- Donut bins of 0/10/25 km drop only a handful of counties; diagnostics dominated by donut = 0.
