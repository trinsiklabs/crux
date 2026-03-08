const { DateTime } = require("luxon");

module.exports = function(eleventyConfig) {
  eleventyConfig.addPassthroughCopy("src/css");
  eleventyConfig.addPassthroughCopy("src/_includes/components");

  // EST timezone for all dates
  eleventyConfig.addFilter("readableDate", dateObj => {
    if (!dateObj) return '';
    return DateTime.fromJSDate(dateObj, { zone: 'America/New_York' })
      .toFormat('MMMM d, yyyy');
  });

  eleventyConfig.addFilter("htmlDateString", dateObj => {
    if (!dateObj) return '';
    return DateTime.fromJSDate(dateObj, { zone: 'America/New_York' })
      .toFormat('yyyy-MM-dd');
  });

  eleventyConfig.addFilter("readableDateWithTime", dateObj => {
    if (!dateObj) return '';
    return DateTime.fromJSDate(dateObj, { zone: 'America/New_York' })
      .toFormat('MMMM d, yyyy h:mm a') + ' EST';
  });
  
  eleventyConfig.addFilter("limit", function (arr, limit) {
    if (!arr) return [];
    return arr.slice(0, limit);
  });

  eleventyConfig.addCollection("post", function(collectionApi) {
    // Include both direct .md files and subdirectory index.md files
    return collectionApi.getFilteredByGlob(["src/blog/*.md", "src/blog/*/index.md"]).sort((a, b) => {
      return b.date - a.date;
    });
  });

  return {
    dir: {
      input: "src",
      output: "_site",
      includes: "_includes",
      data: "_data"
    },
    templateFormats: ["md", "njk", "html"],
    markdownTemplateEngine: "njk",
    htmlTemplateEngine: "njk",
    dataTemplateEngine: "njk"
  };
};
