# makefun-news-image-20261120

[![make.fun · news-image-20261120](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![rank](https://make.fun/badge/news-image-20261120/tngrha/makefun-news-image-20261120/rank.svg)](https://make.fun/bounty/news-image-20261120/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![reward](https://make.fun/badge/news-image-20261120/tngrha/makefun-news-image-20261120/reward.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)

The World on One Page — Friday 20 November 2026: a pure-stdlib Python program that draws a 1024x1024 newspaper front page summing up the day's world news in 35 verified stories across 6 continents — 1 hero, 11 illustrated panels with color-coded region badges, a numbered world map, and 23 one-line briefs, each with one concrete number or fact.

The front page leads with Trump, Xi and Putin holding their first three-way summit in Shenzhen, and covers Russia's 110-missile overnight strike on Kyiv, Anthropic's record $81.3B Nasdaq IPO, the ICJ's genocide ruling against Myanmar, a Houthi missile hitting Riyadh's tallest tower, the COP31 draft dropping fossil-fuel phase-out language, Poland reporting a Russian airspace violation, a fifth straight day of stock-market falls, India opening its firing ranges to Japanese missile drills, DR Congo's Ebola outbreak (11,376 cases), the US–Venezuela military cooperation deal, and Voyager 1 reaching one light-day from Earth. Every story was verified against news reports published on 20 November 2026 (BBC, Reuters, AFP, AP, CNN, WSJ, UN News, Al Jazeera, The Guardian, ECDC, France 24); disputed claims are attributed.

`main.py` uses only the Python 3.13 standard library: it embeds its own 5x7 bitmap font, flat geometric pictograms, simplified continent polygons for the map, and its own PNG writer. It needs no network and writes byte-identical output on repeat runs.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

This writes `out/entry.png` (1024x1024, under 1 MiB).

---

Built for the [make.fun](https://make.fun) competition `news-image-20261120`.
