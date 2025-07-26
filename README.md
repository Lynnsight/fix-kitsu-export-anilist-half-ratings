# fix-kitsu-export-anilist-half-ratings
When exporting from kitsu to anilist, a MAL format is used, which loses half-star ratings (7.5 becomes 7, etc)

This script aims to 
- automatically pull your ratings from Kitsu,
- filter for half-ratings,
- then map those to anilist ids via MAL ids,
- then post updates to anilist


