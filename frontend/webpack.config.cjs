const webpack = require('webpack');
const { resolve } = require('path');

module.exports = {
  devtool: 'inline-source-map',

  entry: {
    // Existing global bundle (unchanged)
    bonsai: resolve(__dirname, 'web/js/bonsai'),

    // New view-level entry
    'group-editor': resolve(
      __dirname,
      'web/js/views/group-editor/index'
    ),
  },

  output: {
    path: resolve(__dirname, 'build/js'),
    filename: '[name].min.js',
    library: 'bonsai',
    libraryTarget: 'umd',
    clean: true,
  },

  resolve: {
    extensions: ['.ts', '.tsx', '.js', '.jsx'],

    // Optional but recommended: semantic aliases
    alias: {
      core: resolve(__dirname, 'web/js/core'),
      components: resolve(__dirname, 'web/js/components'),
      utils: resolve(__dirname, 'web/js/utils'),
      views: resolve(__dirname, 'web/js/views'),
    },
  },

  module: {
    rules: [
      {
        test: /\.css$/i,
        use: ['style-loader', 'css-loader'],
      },
      {
        test: /\.(ts|tsx)$/,
        loader: 'ts-loader',
        exclude: /node_modules/,
        options: {
          transpileOnly: true,
        },
      },
    ],
  },

  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        shared: {
          name: 'shared',
          minChunks: 2,
          priority: 10,
          reuseExistingChunk: true,
        },
      },
    },
  },

  plugins: [
    new webpack.ProvidePlugin({
      process: 'process/browser',
    }),
  ],

  mode: 'development',
};