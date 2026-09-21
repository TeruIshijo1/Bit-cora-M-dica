export interface CamaApi {
  id?: number;
  RoomCode?: string | number;
  RoomName?: string;
  numero_cama?: string;
  numero?: string;
  Estatus?: string;
  estado?: string;
  estado_limpieza?: string;
  PTNum?: string | number;
}

export interface PacienteApi {
  id: number;
  cama_id?: number;
  estado?: string;
  status_ingreso?: string;
  nombre_completo: string;
  num_habitacion?: string;
  area_hospitalaria?: string;
}

export interface MedicoApi {
  id: number;
  nombre_completo: string;
}

export interface CatalogoApi {
  id: number;
  nombre: string;
}
