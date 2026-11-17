# Sensory hard tests v0 (observer only)

Research branch: `test/heartbeat-profile-entropy-trace-v0`. No engine source,
policy or checkpoint is edited. Script: `run_observer_sensory_hard_tests.py`.
Recorded run: `curriculum_packs/reports/sensory_hard_report_seed3101.json`.

Each scene is a synthetic 96x96, 5 fps video (or a one-second audio clip)
imported through `VerdantMediaGateway` and `VerdantPerceptionPipeline` with
default perceptual and objecthood policies. Ground truth stays in the script.

## Observed

| Scene | True objects | Candidates | Result |
|---|---:|---:|---|
| Single moving square | 1 | 1 | Tracked every frame |
| Two distinct objects | 2 | 2 | Each tracked separately |
| Identical objects crossing | 2 | 2 | Both identities kept through the overlap (13 of 13 sightings each) |
| Hidden 2 frames | 1 | 1 | One occlusion and one reappearance recorded |
| Hidden 8 frames | 1 | 2 | Split, as `maximum_occlusion_gap` 6 requires; first left `occluded` |
| Pixel noise, sigma 14 and 40 | 1 | 1 | No spurious regions |
| Lighting ramp | 1 | 1 | Tracked |
| Three static patches and a mover | 4 | 4 | All separate |
| Scale change | 1 | 1 | One identity while growing 8 to 52 px |
| Dark on bright | 1 | 1 | Tracked |
| Nothing moves | 1 | 1 | Common-motion count 0, support 0.275 |
| Blank frames | 0 | 0 | No regions invented |
| Same object, second video | 1 | 1 | One candidate spanning two episodes |
| Different object, second video | 2 | 2 | New candidate |
| Contrast 30 grey levels | 1 | 1 | Tracked |
| Contrast 15 grey levels | 1 | 0 | Below `minimum_saliency_threshold`; not seen |
| 3x3 pixel dot | 1 | 0 | Below `minimum_region_area_fraction`; not seen |
| Sixteen objects | 16 | 12 | Capped by `maximum_regions_per_frame` |
| Red on green, equal luma | 1 | 0 | Not seen: detection is grayscale |
| Whole view pans | 3 | 3 | All three gain common-motion support from the pan |
| Bar rotating 90 degrees | 1 | 2 | One sighting split into a second candidate |
| Abrupt dimming 230 to 90 | 1 | 2 | Treated as a new object |
| Slab covering 60% of frame | 1 | 1 | Tracked; recorded position off the true centre in 6 of 10 frames |
| Two identical squares swap while hidden | 2 | 2 | Each candidate follows its place, so each ends on the other square |
| White square over a brightness ramp | 1 | 3 | Two candidates on background; the real object lost for 4 frames |

Audio (seven clips): all features finite, including on silence. The spectral
signature of a 440 Hz tone and the same tone ten times quieter differ by
0.0009; 440 Hz against 1760 Hz differs by 1.414; against white noise 1.226.

A repeat of the baseline scene in a fresh kernel gave the same fingerprint.

## Claim boundary

**OBSERVED:** On flat backgrounds the region, tracking, occlusion and
cross-episode behaviour matched the scene in every case the stated policy
covers, and the declared limits (contrast, size, region cap, occlusion gap)
held exactly. Over a non-uniform background the median-deviation saliency
produced two persistent candidates on the background itself, with support
scores (0.50, 0.575) above the real object's (0.425), and those background
regions accumulated common-motion counts.

**PROPOSED:** Test saliency against a local or temporal reference instead of
the global median, as an observer-only comparison first. Record a short real
camera clip and repeat this table on it.

**MISSING:** No real camera footage, colour, stereo, or compressed-audio
input. One seed. Objects are axis-aligned squares on synthetic fields. The
slab position error and the rotation split are not diagnosed. Object
promotion was not exercised: no candidate here met every objecthood gate.
