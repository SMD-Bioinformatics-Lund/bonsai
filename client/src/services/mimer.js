import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react'

const { REACT_APP_API_URL } = process.env

// Define user interaction service

// converts an object into a query string
// ex {region: 8:12-55} --> &region=8:12-55
const objectToQueryString = (obj) => Object.keys(obj).map(key => key + '=' + obj[key]).join('&')


export const mimerApi = createApi({
  reducerPath: 'mimerApi',
  baseQuery: fetchBaseQuery({ 
    baseUrl: REACT_APP_API_URL,
    prepareHeaders: (headers, { getState }) => {
      const token = getState().auth.token
      if (token) {
        headers.set('Authorization', `Bearer ${token}`)
      }
      return headers
    }
  }),
  endpoints: (build) => ({
    login: build.mutation({
      query: (credentials) => ({
        url: '/token',
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: objectToQueryString(credentials),
        validateStatus: (response, result) => response.status === 200 && result.access_token
      }),
    }),
    getCurrentUser: build.query({
      query: () => `/users/me`
    }),
    getGroups: build.query({
      query: () => `/groups/`
    }),
    getGroupById: build.query({
      query: (groupId) => `/groups/${groupId}`
    }),
    getSamples: build.query({
      query: () => `/samples/`
    }),
    getSampleById: build.query({
      query: (sampleId) => `/samples/${sampleId}`
    }),
    getLocations: build.query({
      query: () => `/locations`
    }),
    createLocation: build.mutation({
      query: initalLocation => ({
        url: '/locations',
        method: 'POST',
        body: initalLocation
      })
    }),
    getLocationsByBbox: build.query({
      query: (left, bottom, right, top) => `/locations/bbox?left=${left}&bottom=${bottom}&right=${right}&top=${top}`
    }),
    getLocationByIo: build.query({
      query: (locationId) => `/locations/${locationId}`
    }),
  })
})

export const { useLoginMutation, useGetGroupsQuery, useGetGroupByIdQuery, useGetSampleByIdQuery, useGetCurrentUserQuery, useCreateLocationMutation } = mimerApi