import { useMutation } from '@tanstack/react-query';
import api from '../api/client';
import { PipelineRunRequest, PipelineRunTriggerResponse } from '../types/pipeline';

const runPipeline = async (payload: PipelineRunRequest) => {
  const response = await api.post<PipelineRunTriggerResponse>('/v1/pipeline/run', payload);
  return response.data;
};

export const usePipelineRun = () => {
  return useMutation({
    mutationFn: runPipeline
  });
};
