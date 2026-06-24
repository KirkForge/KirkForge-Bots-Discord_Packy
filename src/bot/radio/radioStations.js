// radioStations.js — Danish and international radio station registry
// PackyRadio: because even a grumpy old laptop needs tunes

export const RADIO_STATIONS = [
  {
    id: "drp1",
    name: "DR P1",
    description: "News, debates, and documentaries. The serious one.",
    url: "http://live-icy.gss.dr.dk:8000/A/A03H.mp3",
    category: "DR",
    country: "DK",
    lang: "da",
  },
  {
    id: "drp2",
    name: "DR P2",
    description: "Classical music and culture. For when you're feeling fancy.",
    url: "http://live-icy.gss.dr.dk:8000/A/A04H.mp3",
    category: "DR",
    country: "DK",
    lang: "da",
  },
  {
    id: "drp3",
    name: "DR P3",
    description: "Pop, hits, and youth radio. The cool kid.",
    url: "http://live-icy.gss.dr.dk:8000/A/A05H.mp3",
    category: "DR",
    country: "DK",
    lang: "da",
  },
  {
    id: "drp4",
    name: "DR P4 København",
    description: "Regional radio for Copenhagen. Traffic jams included.",
    url: "http://live-icy.gss.dr.dk:8000/A/A08H.mp3",
    category: "DR",
    country: "DK",
    lang: "da",
  },
  {
    id: "drp4oest",
    name: "DR P4 Østjylland",
    description: "Regional radio for East Jutland. Aarhus represent.",
    url: "http://live-icy.gss.dr.dk:8000/A/A14H.mp3",
    category: "DR",
    country: "DK",
    lang: "da",
  },
  {
    id: "drp4nord",
    name: "DR P4 Nordjylland",
    description: "Regional radio for North Jutland. Cold but cozy.",
    url: "http://live-icy.gss.dr.dk:8000/A/A10H.mp3",
    category: "DR",
    country: "DK",
    lang: "da",
  },
  {
    id: "drp4syd",
    name: "DR P4 Syd",
    description: "Regional radio for Southern Denmark. Flensburg-adjacent.",
    url: "http://live-icy.gss.dr.dk:8000/A/A12H.mp3",
    category: "DR",
    country: "DK",
    lang: "da",
  },
  {
    id: "drp5",
    name: "DR P5",
    description: "Danish music and nostalgia. For the old souls.",
    url: "http://live-icy.gss.dr.dk:8000/A/A25H.mp3",
    category: "DR",
    country: "DK",
    lang: "da",
  },
  {
    id: "drp6",
    name: "DR P6 Beat",
    description: "Electronic and alternative. Packy's thermal throttling jams.",
    url: "http://live-icy.gss.dr.dk:8000/A/A29H.mp3",
    category: "DR",
    country: "DK",
    lang: "da",
  },
  {
    id: "drp8",
    name: "DR P8 Jazz",
    description: "Jazz. Smooth enough to cool a 105°C CPU.",
    url: "http://live-icy.gss.dr.dk:8000/A/A22H.mp3",
    category: "DR",
    country: "DK",
    lang: "da",
  },
  {
    id: "drp7",
    name: "DR P7 Mix",
    description: "Mixed hits. The playlist is as chaotic as Packy's mood.",
    url: "http://live-icy.gss.dr.dk:8000/A/A21H.mp3",
    category: "DR",
    country: "DK",
    lang: "da",
  },
  {
    id: "drp13",
    name: "DR Ramasjang",
    description: "Kids radio. Yes, Packy knows about it. Don't judge.",
    url: "http://live-icy.gss.dr.dk:8000/A/A24H.mp3",
    category: "DR",
    country: "DK",
    lang: "da",
  },
  {
    id: "nova",
    name: "Nova FM",
    description: "Commercial pop hits. Sponsored by capitalism.",
    url: "http://stream.novafm.dk/nova128",
    category: "Commercial",
    country: "DK",
    lang: "da",
  },
  {
    id: "voice",
    name: "The Voice",
    description: "Hits and pop. The voice of the Danish radio dial.",
    url: "http://stream.voice.dk/voice128",
    category: "Commercial",
    country: "DK",
    lang: "da",
  },
  {
    id: "radio4",
    name: "Radio4",
    description: "National commercial talk radio. The 24syv successor.",
    url: "https://live.radio4.dk/radio4",
    category: "Commercial",
    country: "DK",
    lang: "da",
  },
  {
    id: "go",
    name: "GO FM",
    description: "Youth pop and hits. For the young meatbags.",
    url: "https://live.go-fm.dk/go",
    category: "Commercial",
    country: "DK",
    lang: "da",
  },
  {
    id: "popfm",
    name: "Pop FM",
    description: "Classic pop. Remember when music was on CDs? Packy does.",
    url: "https://live.popfm.dk/pop",
    category: "Commercial",
    country: "DK",
    lang: "da",
  },
  {
    id: "myrock",
    name: "MyRock",
    description: "Rock music. Packy's fans spin at maximum RPM for this.",
    url: "https://live.myrock.dk/myrock",
    category: "Commercial",
    country: "DK",
    lang: "da",
  },
  {
    id: "classical",
    name: "Classic FM",
    description: "Classical music. Even a Packard Bell has culture.",
    url: "https://live.classicalfm.dk/classical",
    category: "Commercial",
    country: "DK",
    lang: "da",
  },
  {
    id: "bbc6",
    name: "BBC Radio 6 Music",
    description: "Alternative and indie from the UK. For when Denmark is too small.",
    url: "http://as-hls-ww-live.akamaized.net/pool_904/live/ww/bbc_6music/bbc_6music.isml/bbc_6music-audio%3d128000.norewind.m3u8",
    category: "International",
    country: "UK",
    lang: "en",
  },
  {
    id: "fip",
    name: "FIP Radio",
    description: "Eclectic French music. Packy has sophisticated taste.",
    url: "https://direct.fipradio.fr/live/fip-midfi.mp3",
    category: "International",
    country: "FR",
    lang: "fr",
  },
  {
    id: "nrk",
    name: "NRK P3",
    description: "Norwegian pop and youth. The cooler Nordic cousin.",
    url: "https://lyd.nrk.no/nrk_radio_p3_mp3_h",
    category: "International",
    country: "NO",
    lang: "no",
  },
  {
    id: "sverige",
    name: "Sveriges Radio P3",
    description: "Swedish pop and culture. Don't tell Packy it's Swedish.",
    url: "http://sverigesradio.se/topsy/direkt/164-hi-mp3",
    category: "International",
    country: "SE",
    lang: "sv",
  },
];

export function getStation(id) {
  return RADIO_STATIONS.find((s) => s.id === id.toLowerCase()) || null;
}

export function getStationsByCategory(category) {
  return RADIO_STATIONS.filter(
    (s) => s.category.toLowerCase() === category.toLowerCase()
  );
}

export function listStationIds() {
  return RADIO_STATIONS.map((s) => s.id);
}

export function getCategories() {
  return [...new Set(RADIO_STATIONS.map((s) => s.category))];
}
