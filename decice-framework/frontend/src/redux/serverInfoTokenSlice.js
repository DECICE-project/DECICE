import { createSlice } from '@reduxjs/toolkit';
const server_ip =
    import.meta.env.VITE_SERVER_IP;
const watmon_api_ip =
    import.meta.env.VITE_WATMON_API_IP;
const initialState = {
    value: localStorage.getItem('server_ip') || server_ip,
    watmon_api_ip: localStorage.getItem('watmon_api_ip') || watmon_api_ip,
};

const serverIPSlice = createSlice({
    name: 'serverIP',
    initialState,
    reducers: {
        changeServerIP: (state, action) => {
            state.value = action.payload;
        },
        changeWatmonApiIP: (state, action) => {
            state.watmon_api_ip = action.payload;
        },
    },
});

export const { changeServerIP, changeWatmonApiIP } = serverIPSlice.actions;
export default serverIPSlice.reducer;