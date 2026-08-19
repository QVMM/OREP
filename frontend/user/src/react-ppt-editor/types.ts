export type SlideDocumentElementType = "text" | "rect" | "image" | "table";

export interface SlideDocumentElement {
  id: string;
  type: SlideDocumentElementType;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation?: number;
  sourceTag?: string;
  sourceIndex?: number;
  committed?: boolean;
  [key: string]: unknown;
}

export interface SlideDocument {
  version: number;
  width: number;
  height: number;
  backgroundSvg: string;
  speakerNotes?: string;
  elements: SlideDocumentElement[];
}

export interface PreviewSlide {
  index: number;
  name: string;
  source?: string;
  content: string;
  notes?: string;
  document?: SlideDocument | null;
}
