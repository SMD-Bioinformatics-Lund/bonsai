const webpack = require('webpack');
const { WebpackManifestPlugin } = require('webpack-manifest-plugin');
const { resolve } = require('path');

const isProduction = process.env.NODE_ENV === 'production';

module.exports = {
  devtool: 'inline-source-map',

  entry: {
    // New view-level entries
    'group-editor': resolve(
      __dirname,
      'web/js/views/group-editor/index'
    ),
    'group-view': resolve(__dirname, 'web/js/views/groups-view/index'),
    'sample-view': resolve(__dirname, 'web/js/views/sample-view/index'),
    'variants-table': resolve(__dirname, 'web/js/views/variants-table/index'),
  },

  output: {
    path: resolve(__dirname, 'build'),
    filename: '[name].[contenthash].bundle.js',
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
    runtimeChunk: 'single',
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendor',
          chunks: 'all',
          priority: 20,
        },
        commons: {
          name: 'commons',
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
    new WebpackManifestPlugin(),
  ],

  mode: isProduction ? 'production' : 'development',
};